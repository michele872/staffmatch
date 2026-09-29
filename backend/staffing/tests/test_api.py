from unittest import mock

from rest_framework.test import APITestCase

from staffing.models import Role
from staffing.services.ai_intake import AIIntakeError, ShiftDraft, RequirementDraft
from staffing.tests.factories import MILANO, MONZA, make_city, make_shift, make_staff


class ShiftApiTests(APITestCase):
    def setUp(self):
        self.milano = make_city("Milano", MILANO)
        self.monza = make_city("Monza", MONZA)

    def test_create_shift_with_requirements(self):
        response = self.client.post(
            "/api/shifts/",
            {
                "title": "Day shift",
                "date": "2030-06-14",
                "city": self.milano.id,
                "patients": 80,
                "notes": "",
                "requirements": [
                    {"role": Role.NURSE, "quantity": 1},
                    {"role": Role.CARE_ASSISTANT, "quantity": 4},
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(len(response.data["requirements"]), 2)

    def test_rejects_duplicate_roles(self):
        response = self.client.post(
            "/api/shifts/",
            {
                "title": "Day shift", "date": "2030-06-14", "city": self.milano.id, "patients": 80,
                "requirements": [
                    {"role": Role.NURSE, "quantity": 1},
                    {"role": Role.NURSE, "quantity": 2},
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("requirements", response.data)

    def test_list_shows_required_and_assigned_totals(self):
        make_staff("A", self.milano)
        shift = make_shift(self.milano, {Role.CARE_ASSISTANT: 2, Role.NURSE: 1})
        self.client.post(f"/api/shifts/{shift.id}/assign/")

        response = self.client.get("/api/shifts/")

        self.assertEqual(response.data[0]["required_staff"], 3)
        self.assertEqual(response.data[0]["assigned_staff"], 1)

    def test_plan_then_assign(self):
        make_staff("Near", self.monza)
        make_staff("Local", self.milano)
        shift = make_shift(self.milano, {Role.CARE_ASSISTANT: 2})

        plan = self.client.get(f"/api/shifts/{shift.id}/plan/").data
        self.assertEqual(
            [c["staff_name"] for c in plan[0]["candidates"]], ["Local", "Near"]
        )

        detail = self.client.post(f"/api/shifts/{shift.id}/assign/").data
        self.assertEqual(len(detail["assignments"]), 2)

    def test_remove_assignment_frees_the_position(self):
        make_staff("Local", self.milano)
        shift = make_shift(self.milano, {Role.CARE_ASSISTANT: 1})
        assignment_id = self.client.post(f"/api/shifts/{shift.id}/assign/").data[
            "assignments"
        ][0]["id"]

        response = self.client.delete(f"/api/assignments/{assignment_id}/")

        self.assertEqual(response.status_code, 204)
        self.assertEqual(shift.assignments.count(), 0)


class DraftFromTextApiTests(APITestCase):
    def setUp(self):
        self.milano = make_city("Milano", MILANO)

    @mock.patch("staffing.services.ai_intake.is_enabled", return_value=True)
    @mock.patch("staffing.views.ai_intake.draft_shift")
    def test_returns_draft_with_city_id(self, draft_shift, _enabled):
        draft_shift.return_value = ShiftDraft(
            title="Turno di notte", date="2030-06-14", city="Milano", patients=60,
            requirements=[RequirementDraft(role="CARE_ASSISTANT", quantity=4)], notes="",
        )

        response = self.client.post(
            "/api/shifts/draft-from-text/", {"text": "4 OSS a Milano"}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["city"], self.milano.id)
        self.assertEqual(response.data["requirements"], [{"role": "CARE_ASSISTANT", "quantity": 4}])

    @mock.patch("staffing.views.ai_intake.draft_shift", side_effect=AIIntakeError("down"))
    def test_ai_errors_become_502(self, _draft_shift):
        response = self.client.post(
            "/api/shifts/draft-from-text/", {"text": "something"}, format="json"
        )

        self.assertEqual(response.status_code, 502)

    def test_disabled_without_api_key(self):
        with self.settings(ANTHROPIC_API_KEY=""):
            meta = self.client.get("/api/meta/").data
            response = self.client.post(
                "/api/shifts/draft-from-text/", {"text": "something"}, format="json"
            )

        self.assertFalse(meta["ai_intake_enabled"])
        self.assertEqual(response.status_code, 503)
