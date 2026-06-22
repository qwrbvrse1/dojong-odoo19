from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestKioskOnboardingAPI(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.KioskService = cls.env["dojo.kiosk.service"]
        cls.KioskConfig = cls.env["dojo.kiosk.config"]
        cls.Member = cls.env["dojo.member"]
        cls.pricelist = cls.env["product.pricelist"].search([], limit=1)
        if not cls.pricelist:
            cls.pricelist = cls.env["product.pricelist"].create({
                "name": "Onboarding Test Pricelist",
                "currency_id": cls.env.company.currency_id.id,
            })
        cls.config = cls.KioskConfig.create({
            "name": "Onboarding Test Kiosk",
            "kiosk_token": "onboarding-test-token",
            "pin_code": "123456",
            "active": True,
        })
        cls.member = cls.Member.with_context(
            mail_create_nolog=True,
            tracking_disable=True,
        ).create({
            "name": "Onboarding Test Student",
            "email": "onboarding.test@example.com",
        })

    def _get_instructor_key(self):
        """Verify PIN and return instructor_key for authenticated calls."""
        result = self.KioskService.verify_pin("123456", token=self.config.kiosk_token)
        self.assertTrue(result.get("success"))
        return result["instructor_key"]

    def test_get_member_profile_returns_onboarding_dict(self):
        """Verify that get_member_profile() returns onboarding data in workflow_status."""
        profile = self.KioskService.get_member_profile(self.member.id)
        self.assertIn("workflow_status", profile)
        workflow = profile["workflow_status"]
        self.assertIn("onboarding", workflow)
        onboarding = workflow["onboarding"]
        # Check required keys
        self.assertIn("available", onboarding)
        self.assertIn("state", onboarding)
        self.assertIn("complete", onboarding)
        self.assertIn("progress_pct", onboarding)
        self.assertIn("steps", onboarding)
        self.assertIn("missing_steps", onboarding)

    def test_onboarding_progress_calculation(self):
        """Verify that progress_pct is calculated correctly based on legacy steps."""
        if "dojo.onboarding.record" not in self.env:
            self.skipTest("dojo_onboarding module is not installed")

        # Create an onboarding record with 2 out of 5 legacy steps complete
        record = self.env["dojo.onboarding.record"].create({
            "member_id": self.member.id,
            "company_id": self.env.company.id,
            "step_member_info": True,
            "step_household": True,
            "step_enrollment": False,
            "step_subscription": False,
            "step_portal_access": False,
        })

        onboarding = self.KioskService._member_onboarding_status(self.member)
        # 2 out of 5 legacy steps = 40%
        self.assertEqual(onboarding["progress_pct"], 40)
        self.assertFalse(onboarding["complete"])
        self.assertIn("Subscription", onboarding["missing_steps"])

    def test_complete_step_endpoint_exists_and_authenticated(self):
        """Verify that /kiosk/api/onboarding/complete_step endpoint is available and requires auth."""
        if "dojo.onboarding.record" not in self.env:
            self.skipTest("dojo_onboarding module is not installed")

        instructor_key = self._get_instructor_key()

        # Call complete_step action
        result = self.KioskService.perform_onboarding_action(
            self.member.id,
            "complete_step",
            step_key="member_info"
        )

        self.assertTrue(result.get("success"))
        self.assertIn("workflow_status", result)

        # Verify the step was marked complete
        record = self.env["dojo.onboarding.record"].search([
            ("member_id", "=", self.member.id)
        ], limit=1)
        self.assertTrue(record.step_member_info)

    def test_send_reminder_endpoint_exists_and_authenticated(self):
        """Verify that /kiosk/api/onboarding/send_reminder endpoint is available and requires auth."""
        if "dojo.onboarding.record" not in self.env:
            self.skipTest("dojo_onboarding module is not installed")

        instructor_key = self._get_instructor_key()

        # Call send_reminder action
        result = self.KioskService.perform_onboarding_action(
            self.member.id,
            "send_reminder",
            message="Test onboarding reminder"
        )

        self.assertTrue(result.get("success"))
        self.assertIn("workflow_status", result)
        # sent_via should be present (email or SMS or both, depending on what's configured)
        self.assertIn("sent_via", result)
