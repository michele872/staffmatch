"""AI-assisted shift intake.

Care facilities usually send staffing requests as free text ("we need 2 nurses
and 3 care assistants for the night shift in Bergamo on 14 June, 60 patients").
This service asks Claude to turn that text into a structured draft that the
user reviews in the shift form before saving. Nothing is saved automatically.
"""

from datetime import date
from typing import Literal

import anthropic
from django.conf import settings
from pydantic import BaseModel, Field

from staffing.models import Role

SYSTEM_PROMPT = """\
You turn staffing requests from care facilities (nursing homes, clinics,
home-care services) into a structured draft of a work shift.
The draft is reviewed by a person before it is saved, so leave a field empty
(null) when the request does not say it clearly instead of guessing.

Rules:
- city must be exactly one of the known cities listed in the request, or null.
- date must be an ISO date (YYYY-MM-DD). Resolve relative dates ("next Saturday")
  against today's date given in the request. Use null if no date is given.
- requirements lists only the roles explicitly requested, with their quantity.
- title is a short name for the shift, in the language of the request.
- patients is the number of patients to look after during the shift, or null.
- notes keeps any useful detail that does not fit the other fields (shift hours,
  ward, special skills), in the language of the request.
"""


class RequirementDraft(BaseModel):
    role: Literal["NURSE", "CARE_ASSISTANT", "PHYSIOTHERAPIST", "DOCTOR"]
    quantity: int = Field(ge=1)


class ShiftDraft(BaseModel):
    title: str
    date: str | None
    city: str | None
    patients: int | None
    requirements: list[RequirementDraft]
    notes: str


class AIIntakeError(Exception):
    """The request could not be turned into a draft."""


class AIIntakeDisabled(AIIntakeError):
    """No API key is configured."""


def is_enabled() -> bool:
    return bool(settings.ANTHROPIC_API_KEY)


def draft_shift(
    text: str,
    known_cities: list[str],
    today: date,
    client: anthropic.Anthropic | None = None,
) -> ShiftDraft:
    """Extract a shift draft from a free-text staffing request."""
    if client is None:
        if not is_enabled():
            raise AIIntakeDisabled("AI intake is disabled: ANTHROPIC_API_KEY is not set.")
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    user_message = (
        f"Today is {today.isoformat()}.\n"
        f"Known cities: {', '.join(known_cities)}.\n"
        f"Available roles: {', '.join(Role.values)}.\n\n"
        f"<request>\n{text}\n</request>"
    )

    try:
        response = client.beta.messages.parse(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=4096,
            # Extraction is a simple task: low effort keeps it fast and cheap.
            output_config={"effort": "low"},
            output_format=ShiftDraft,
            # If the model declines, the API retries on a suitable fallback model.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
    except anthropic.APIConnectionError as exc:
        raise AIIntakeError("Could not reach the AI service.") from exc
    except anthropic.RateLimitError as exc:
        raise AIIntakeError("The AI service is busy, please retry in a minute.") from exc
    except anthropic.APIStatusError as exc:
        raise AIIntakeError(f"The AI service returned an error ({exc.status_code}).") from exc

    if response.stop_reason == "refusal":
        raise AIIntakeError("The AI service declined to process this request.")
    if response.parsed_output is None:
        raise AIIntakeError("The AI service returned an incomplete draft.")

    draft = response.parsed_output
    # Never trust free-form output for foreign keys: keep only known cities.
    if draft.city not in known_cities:
        draft.city = None
    return draft
