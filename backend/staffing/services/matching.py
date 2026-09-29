"""Staff matching: who can work a shift, and who should be picked.

A staff member is a candidate for a role at a shift when they:
  * have that role and are active,
  * are not already assigned to any shift on the same date,
  * live within their own maximum travel distance from the shift city.

Candidates are ranked by distance, so the closest people are picked first.
Distances are computed by PostGIS on geography points, in metres.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from django.contrib.gis.db.models.functions import Distance
from django.db import transaction
from django.db.models import F

from staffing.models import Assignment, Shift, StaffMember


@dataclass(frozen=True)
class Candidate:
    staff: StaffMember
    distance_km: Decimal


@dataclass
class RolePlan:
    role: str
    required: int
    already_assigned: int
    candidates: list[Candidate] = field(default_factory=list)

    @property
    def missing(self) -> int:
        """How many people are still missing after picking the candidates."""
        return max(self.required - self.already_assigned - len(self.candidates), 0)


def find_candidates(shift: Shift, role: str, limit: int | None = None) -> list[Candidate]:
    """Return eligible staff for `role` at `shift`, closest first."""
    queryset = (
        StaffMember.objects.filter(active=True, role=role)
        .exclude(assignments__shift__date=shift.date)
        .select_related("city")
        .annotate(distance=Distance("city__location", shift.city.location))
        .filter(distance__lte=F("max_travel_km") * 1000)
        .order_by("distance", "full_name")
    )
    if limit is not None:
        queryset = queryset[:limit]
    return [
        Candidate(staff=member, distance_km=_to_km(member.distance.m))
        for member in queryset
    ]


def build_plan(shift: Shift) -> list[RolePlan]:
    """Propose the closest available people for every open position of the shift."""
    plans = []
    for requirement in shift.requirements.all():
        already = shift.assignments.filter(role=requirement.role).count()
        still_needed = max(requirement.quantity - already, 0)
        candidates = (
            find_candidates(shift, requirement.role, limit=still_needed) if still_needed else []
        )
        plans.append(
            RolePlan(
                role=requirement.role,
                required=requirement.quantity,
                already_assigned=already,
                candidates=candidates,
            )
        )
    return plans


@transaction.atomic
def assign_staff(shift: Shift) -> list[Assignment]:
    """Fill the open positions of a shift with the best candidates and save them."""
    # Lock the shift row so two concurrent requests cannot double-book positions.
    Shift.objects.select_for_update().get(pk=shift.pk)
    created = []
    for plan in build_plan(shift):
        for candidate in plan.candidates:
            created.append(
                Assignment.objects.create(
                    shift=shift,
                    staff=candidate.staff,
                    role=plan.role,
                    distance_km=candidate.distance_km,
                )
            )
    return created


def _to_km(metres: float) -> Decimal:
    return Decimal(metres / 1000).quantize(Decimal("0.1"))
