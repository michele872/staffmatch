from datetime import date
from decimal import Decimal

from django.test import TestCase

from staffing.models import Assignment, Role
from staffing.services.matching import assign_staff, build_plan, find_candidates
from staffing.tests.factories import (
    BERGAMO, MILANO, MONZA, ROMA, make_city, make_shift, make_staff,
)


class FindCandidatesTests(TestCase):
    def setUp(self):
        self.milano = make_city("Milano", MILANO)
        self.monza = make_city("Monza", MONZA)
        self.bergamo = make_city("Bergamo", BERGAMO)
        self.roma = make_city("Roma", ROMA)

    def test_orders_candidates_by_distance(self):
        far = make_staff("Far", self.bergamo, max_travel_km=100)
        near = make_staff("Near", self.monza)
        local = make_staff("Local", self.milano)
        shift = make_shift(self.milano, {Role.CARE_ASSISTANT: 3})

        candidates = find_candidates(shift, Role.CARE_ASSISTANT)

        self.assertEqual([c.staff for c in candidates], [local, near, far])
        self.assertEqual(candidates[0].distance_km, Decimal("0.0"))

    def test_computes_real_distance_in_km(self):
        make_staff("Near", self.monza)
        shift = make_shift(self.milano, {Role.CARE_ASSISTANT: 1})

        [candidate] = find_candidates(shift, Role.CARE_ASSISTANT)

        self.assertAlmostEqual(float(candidate.distance_km), 15, delta=2)

    def test_respects_each_persons_max_travel_distance(self):
        make_staff("Stays home", self.bergamo, max_travel_km=30)
        willing = make_staff("Travels", self.bergamo, max_travel_km=80)
        shift = make_shift(self.milano, {Role.CARE_ASSISTANT: 2})

        candidates = find_candidates(shift, Role.CARE_ASSISTANT)

        self.assertEqual([c.staff for c in candidates], [willing])

    def test_only_matching_role_and_active_staff(self):
        make_staff("Nurse", self.milano, role=Role.NURSE)
        make_staff("Inactive care assistant", self.milano, active=False)
        assistant = make_staff("Care assistant", self.milano)
        shift = make_shift(self.milano, {Role.CARE_ASSISTANT: 2})

        candidates = find_candidates(shift, Role.CARE_ASSISTANT)

        self.assertEqual([c.staff for c in candidates], [assistant])

    def test_excludes_staff_booked_on_the_same_day(self):
        busy = make_staff("Busy", self.milano)
        free = make_staff("Free", self.milano)
        other_shift = make_shift(self.monza, {Role.CARE_ASSISTANT: 1}, title="Other")
        Assignment.objects.create(
            shift=other_shift, staff=busy, role=Role.CARE_ASSISTANT, distance_km=Decimal("15.0")
        )
        shift = make_shift(self.milano, {Role.CARE_ASSISTANT: 2})

        candidates = find_candidates(shift, Role.CARE_ASSISTANT)

        self.assertEqual([c.staff for c in candidates], [free])

    def test_staff_booked_on_another_day_is_available(self):
        person = make_staff("Person", self.milano)
        earlier = make_shift(self.milano, {Role.CARE_ASSISTANT: 1}, on=date(2030, 6, 13))
        Assignment.objects.create(
            shift=earlier, staff=person, role=Role.CARE_ASSISTANT, distance_km=Decimal("0.0")
        )
        shift = make_shift(self.milano, {Role.CARE_ASSISTANT: 1}, on=date(2030, 6, 14))

        self.assertEqual([c.staff for c in find_candidates(shift, Role.CARE_ASSISTANT)], [person])


class PlanAndAssignTests(TestCase):
    def setUp(self):
        self.milano = make_city("Milano", MILANO)
        self.monza = make_city("Monza", MONZA)

    def test_plan_picks_the_closest_people_up_to_the_quantity(self):
        closest = make_staff("A", self.milano)
        second = make_staff("B", self.milano)
        make_staff("C", self.monza)
        shift = make_shift(self.milano, {Role.CARE_ASSISTANT: 2})

        [plan] = build_plan(shift)

        self.assertEqual([c.staff for c in plan.candidates], [closest, second])
        self.assertEqual(plan.missing, 0)

    def test_plan_reports_missing_positions(self):
        make_staff("Only nurse", self.milano, role=Role.NURSE)
        shift = make_shift(self.milano, {Role.NURSE: 3})

        [plan] = build_plan(shift)

        self.assertEqual(len(plan.candidates), 1)
        self.assertEqual(plan.missing, 2)

    def test_assign_saves_assignments_and_is_idempotent(self):
        make_staff("A", self.milano)
        make_staff("B", self.monza)
        shift = make_shift(self.milano, {Role.CARE_ASSISTANT: 2})

        first_run = assign_staff(shift)
        second_run = assign_staff(shift)

        self.assertEqual(len(first_run), 2)
        self.assertEqual(second_run, [])
        self.assertEqual(shift.assignments.count(), 2)

    def test_assign_fills_only_the_remaining_positions(self):
        make_staff("A", self.milano)
        shift = make_shift(self.milano, {Role.CARE_ASSISTANT: 2})
        assign_staff(shift)
        make_staff("B", self.monza)  # joins the pool later

        assign_staff(shift)

        self.assertEqual(shift.assignments.count(), 2)
