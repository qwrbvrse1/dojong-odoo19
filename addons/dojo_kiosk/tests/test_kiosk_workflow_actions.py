from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.modules.module import get_manifest
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestKioskWorkflowActions(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.KioskService = cls.env["dojo.kiosk.service"]
        cls.KioskConfig = cls.env["dojo.kiosk.config"]
        cls.Program = cls.env["dojo.program"]
        cls.ClassTemplate = cls.env["dojo.class.template"]
        cls.ClassSession = cls.env["dojo.class.session"]
        cls.Plan = cls.env["dojo.subscription.plan"]
        cls.Subscription = cls.env["sale.subscription"]
        cls.pricelist = cls.env["product.pricelist"].search([], limit=1)
        if not cls.pricelist:
            cls.pricelist = cls.env["product.pricelist"].create({
                "name": "Workflow Test Pricelist",
                "currency_id": cls.env.company.currency_id.id,
            })
        cls.program = cls.Program.create({"name": "Workflow Test Program"})
        plan_vals = {
            "name": "Workflow Unlimited Plan",
            "price": 100,
            "program_ids": [(6, 0, cls.program.ids)],
        }
        cls.plan = cls.Plan.create(plan_vals)
        limited_plan_vals = {
            "name": "Workflow Limited Plan",
            "price": 100,
            "program_ids": [(6, 0, cls.program.ids)],
        }
        if "credits_per_period" in cls.Plan._fields:
            limited_plan_vals["credits_per_period"] = 4
        cls.limited_plan = cls.Plan.create(limited_plan_vals)
        cls.member = cls.env["dojo.member"].with_context(
            mail_create_nolog=True,
            tracking_disable=True,
        ).create({
            "name": "Workflow Student",
            "email": "workflow.student@example.com",
        })

    def _member(self, name, membership_state="active"):
        return self.env["dojo.member"].with_context(
            mail_create_nolog=True,
            tracking_disable=True,
        ).create({
            "name": name,
            "email": "%s@example.com" % name.lower().replace(" ", "."),
            "membership_state": membership_state,
        })

    def _session(self, program=None):
        program = program or self.program
        template = self.ClassTemplate.create({
            "name": "Boundary Trial Course",
            "program_id": program.id,
        })
        start = fields.Datetime.now()
        return self.ClassSession.create({
            "template_id": template.id,
            "start_datetime": start,
            "end_datetime": start + timedelta(minutes=60),
            "state": "open",
            "capacity": 20,
        })

    def _subscription(self, member, state="active", plan=None):
        stage_type = {
            "active": "in_progress",
            "paused": "in_progress",
            "pending": "pre",
            "cancelled": "post",
            "expired": "post",
        }[state]
        stage = self.env["sale.subscription.stage"].search(
            [("type", "=", stage_type)],
            limit=1,
        )
        vals = {
            "member_id": member.id,
            "plan_id": (plan or self.plan).id,
            "pricelist_id": self.pricelist.id,
            "stage_id": stage.id,
            "paused": state == "paused",
        }
        if state == "expired":
            reason = self.env.ref(
                "dojo_subscriptions.close_reason_expired",
                raise_if_not_found=False,
            )
            if reason:
                vals["close_reason_id"] = reason.id
        return self.Subscription.create(vals)

    def test_profile_payload_contains_workflow_status(self):
        profile = self.KioskService.get_member_profile(self.member.id)

        self.assertIn("workflow_status", profile)
        self.assertIn("subscription", profile["workflow_status"])
        self.assertIn("grading", profile["workflow_status"])
        if profile["workflow_status"]["onboarding"]["available"]:
            self.assertFalse(profile["workflow_status"]["onboarding"]["complete"])
            self.assertTrue(profile["workflow_status"]["onboarding"]["missing_steps"])
        if profile["workflow_status"]["waiver"]["available"]:
            self.assertFalse(profile["workflow_status"]["waiver"]["signed"])

    def test_workflow_subscription_state_matrix(self):
        active = self._member("Active Workflow Student")
        self._subscription(active, state="active")
        active_status = self.KioskService._member_workflow_status(active)
        self.assertEqual(active_status["subscription"]["state"], "active")
        self.assertTrue(active_status["subscription"]["good_standing"])

        paused = self._member("Paused Workflow Student", membership_state="paused")
        self._subscription(paused, state="paused")
        paused_status = self.KioskService._member_workflow_status(paused)
        self.assertEqual(paused_status["subscription"]["state"], "paused")
        self.assertIn("membership_paused", {
            alert["code"] for alert in paused_status["subscription"]["alerts"]
        })

        cancelled = self._member("Cancelled Workflow Student", membership_state="cancelled")
        self._subscription(cancelled, state="cancelled")
        cancelled_status = self.KioskService._member_workflow_status(cancelled)
        self.assertEqual(cancelled_status["subscription"]["state"], "cancelled")
        self.assertIn("membership_cancelled", {
            alert["code"] for alert in cancelled_status["alerts"]
        })

        no_subscription = self._member("No Subscription Workflow Student")
        no_subscription_status = self.KioskService._member_workflow_status(no_subscription)
        self.assertEqual(no_subscription_status["subscription"]["state"], "none")
        self.assertIn("no_subscription", {
            alert["code"] for alert in no_subscription_status["alerts"]
        })

        if "credits_per_period" in self.Plan._fields:
            exhausted = self._member("Credits Exhausted Workflow Student")
            exhausted_sub = self._subscription(exhausted, state="active", plan=self.limited_plan)
            if exhausted_sub.credit_balance:
                self.env["dojo.credit.transaction"].sudo().create({
                    "subscription_id": exhausted_sub.id,
                    "transaction_type": "adjustment",
                    "amount": -exhausted_sub.credit_balance,
                    "status": "confirmed",
                    "note": "Test credit exhaustion",
                })
                exhausted_sub.invalidate_recordset()
            exhausted_status = self.KioskService._member_workflow_status(exhausted)
            self.assertIn("credits_exhausted", {
                alert["code"] for alert in exhausted_status["subscription"]["alerts"]
            })

    def test_complete_onboarding_step_uses_existing_record(self):
        if "dojo.onboarding.record" not in self.env:
            self.skipTest("dojo_onboarding is not installed")

        result = self.KioskService.perform_onboarding_action(
            self.member.id,
            "complete_step",
            step_key="member_info",
        )
        record = self.env["dojo.onboarding.record"].search(
            [("member_id", "=", self.member.id)],
            limit=1,
        )

        self.assertTrue(result["success"])
        self.assertTrue(record.step_member_info)
        self.assertEqual(result["workflow_status"]["onboarding"]["progress_pct"], record.progress_pct)

    def test_add_note_persists_to_member_chatter(self):
        result = self.KioskService.perform_onboarding_action(
            self.member.id,
            "add_note",
            note="Needs help with uniform sizing.",
        )

        self.assertTrue(result["success"])
        messages = self.env["mail.message"].search([
            ("model", "=", "dojo.member"),
            ("res_id", "=", self.member.id),
            ("body", "ilike", "uniform sizing"),
        ])
        self.assertTrue(messages)

    def test_send_reminder_persists_to_onboarding_audit(self):
        if "dojo.onboarding.record" not in self.env:
            self.skipTest("dojo_onboarding is not installed")

        def fake_send_parent_message(service, member_id, subject, message, **kwargs):
            return {"success": True, "sent_via": ["email"], "recipients": ["Guardian"]}

        with patch.object(type(self.KioskService), "send_parent_message", fake_send_parent_message):
            result = self.KioskService.perform_onboarding_action(
                self.member.id,
                "send_reminder",
                message="Please finish onboarding before class.",
            )

        record = self.env["dojo.onboarding.record"].search(
            [("member_id", "=", self.member.id)],
            limit=1,
        )
        messages = self.env["mail.message"].search([
            ("model", "=", "dojo.onboarding.record"),
            ("res_id", "=", record.id),
            ("body", "ilike", "Please finish onboarding"),
        ])

        self.assertTrue(result["success"])
        self.assertTrue(messages)

    def test_escalate_blocker_creates_instructor_task_and_audit(self):
        if "dojo.onboarding.record" not in self.env:
            self.skipTest("dojo_onboarding is not installed")

        profile = self.env["dojo.instructor.profile"].sudo().search(
            [("user_id", "=", self.env.user.id)],
            limit=1,
        )
        if not profile:
            self.env["dojo.instructor.profile"].sudo().create({
                "name": "Workflow Instructor",
                "user_id": self.env.user.id,
                "partner_id": self.env.user.partner_id.id,
                "company_id": self.member.company_id.id,
            })

        result = self.KioskService.perform_onboarding_action(
            self.member.id,
            "escalate_blocker",
            step_key="subscription",
            note="Payment method is blocked.",
        )
        task = self.env["project.task"].sudo().search([
            ("name", "ilike", "Onboarding blocker: Workflow Student"),
            ("name", "ilike", "Subscription"),
        ], limit=1)
        record = self.env["dojo.onboarding.record"].search(
            [("member_id", "=", self.member.id)],
            limit=1,
        )
        messages = self.env["mail.message"].search([
            ("model", "=", "dojo.onboarding.record"),
            ("res_id", "=", record.id),
            ("body", "ilike", "Payment method is blocked"),
        ])

        self.assertTrue(result["success"])
        self.assertTrue(task)
        self.assertTrue(messages)

    def test_onboarding_action_whitelist_rejects_unsupported_edits(self):
        original_state = self.member.membership_state

        unsupported = self.KioskService.perform_onboarding_action(
            self.member.id,
            "set_membership_state",
            note="active",
        )
        invalid_step = self.KioskService.perform_onboarding_action(
            self.member.id,
            "complete_step",
            step_key="membership_state",
        )
        self.member.invalidate_recordset()

        self.assertFalse(unsupported["success"])
        self.assertFalse(invalid_step["success"])
        self.assertEqual(self.member.membership_state, original_state)

    def test_kiosk_manifest_keeps_crm_and_ai_optional(self):
        deps = set(get_manifest("dojo_kiosk").get("depends") or [])

        self.assertNotIn("dojo_crm", deps)
        self.assertNotIn("ai_assistant", deps)
        self.assertIn("dojo_core", deps)

    def test_bootstrap_reports_optional_boundary_flags(self):
        config = self.KioskConfig.create({
            "name": "Boundary Optional Kiosk",
            "pin_code": "123456",
        })
        payload = self.KioskService.get_config_bootstrap(config.kiosk_token)

        self.assertEqual(payload["ai_enabled"], "ai.assistant.service" in self.env)
        self.assertEqual(
            payload["trial_leads_enabled"],
            self.KioskService.is_trial_lead_adapter_available(),
        )

    def test_optional_crm_trial_paths_are_disabled_without_trial_adapter(self):
        if self.KioskService.is_trial_lead_adapter_available():
            self.skipTest("dojo_crm trial lead adapter is installed")

        self.assertEqual(self.KioskService.search_trial_leads("Trial Student"), [])
        result = self.KioskService.checkin_trial_lead(999999)

        self.assertFalse(result["success"])
        self.assertIn("not installed", result["error"])

    def test_optional_crm_trial_paths_remain_compatible_when_adapter_installed(self):
        if not self.KioskService.is_trial_lead_adapter_available():
            self.skipTest("dojo_crm trial lead adapter is not installed")

        session = self._session()
        lead = self.env["crm.lead"].create({
            "name": "Boundary Trial Student",
            "contact_name": "Boundary Trial Student",
            "email_from": "boundary.trial@example.com",
            "trial_session_id": session.id,
            "trial_attended": False,
            "dojo_member_id": False,
        })

        results = self.KioskService.search_trial_leads("Boundary Trial")
        checkin = self.KioskService.checkin_trial_lead(lead.id, session_id=session.id)
        lead.invalidate_recordset()

        self.assertIn(lead.id, {result["lead_id"] for result in results})
        self.assertTrue(checkin["success"], checkin.get("error"))
        self.assertTrue(lead.trial_attended)
