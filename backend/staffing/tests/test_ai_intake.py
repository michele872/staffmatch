from datetime import date
from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase

from staffing.services.ai_intake import (
    AIIntakeError, ShiftDraft, RequirementDraft, draft_shift,
)


def fake_client(parsed_output, stop_reason="end_turn"):
    client = mock.Mock()
    client.beta.messages.parse.return_value = SimpleNamespace(
        stop_reason=stop_reason, parsed_output=parsed_output
    )
    return client


class DraftShiftTests(SimpleTestCase):
    def draft(self, **overrides):
        values = dict(
            title="Turno di notte", date="2030-06-14", city="Bergamo", patients=60,
            requirements=[RequirementDraft(role="CARE_ASSISTANT", quantity=6)], notes="",
        )
        values.update(overrides)
        return ShiftDraft(**values)

    def test_sends_known_cities_and_today_to_the_model(self):
        client = fake_client(self.draft())

        draft_shift("6 OSS a Bergamo", ["Bergamo", "Milano"], date(2030, 1, 1), client)

        kwargs = client.beta.messages.parse.call_args.kwargs
        user_message = kwargs["messages"][0]["content"]
        self.assertIn("Today is 2030-01-01", user_message)
        self.assertIn("Known cities: Bergamo, Milano", user_message)
        self.assertIs(kwargs["output_format"], ShiftDraft)

    def test_unknown_city_is_dropped(self):
        client = fake_client(self.draft(city="Atlantis"))

        draft = draft_shift("text", ["Bergamo"], date(2030, 1, 1), client)

        self.assertIsNone(draft.city)

    def test_refusal_raises(self):
        client = fake_client(None, stop_reason="refusal")

        with self.assertRaises(AIIntakeError):
            draft_shift("text", ["Bergamo"], date(2030, 1, 1), client)

    def test_missing_output_raises(self):
        client = fake_client(None)

        with self.assertRaises(AIIntakeError):
            draft_shift("text", ["Bergamo"], date(2030, 1, 1), client)
