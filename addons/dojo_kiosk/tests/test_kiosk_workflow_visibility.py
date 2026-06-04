from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestKioskWorkflowVisibility(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.KioskService = cls.env["dojo.kiosk.service"]
        cls.Program = cls.env["dojo.program"]
        cls.ClassTemplate = cls.env["dojo.class.template"]
        cls.ClassSession = cls.env["dojo.class.session"]
        cls.Enrollment = cls.env["dojo.class.enrollment"]
        cls.Member = cls.env["dojo.member"]
        cls.AttendanceLog = cls.env["dojo.attendance.log"]
        cls.BeltRank = cls.env["dojo.belt.rank"]
        cls.MemberRank = cls.env["dojo.member.rank"]
        cls.Plan = cls.env["dojo.subscription.plan"]
        cls.Subscription = cls.env["sale.subscription"]
        cls.Task = cls.env["project.task"]
        cls.pricelist = cls.env["product.pricelist"].search([], limit=1)
        if not cls.pricelist:
            cls.pricelist = cls.env["product.pricelist"].create({
                "name": "Workflow Visibility Pricelist",
                "currency_id": cls.env.company.currency_id.id,
            })
        cls.program = cls.Program.create({"name": "Workflow Visibility Program"})
        cls.template = cls.ClassTemplate.create({
            "name": "Workflow Visibility Course",
            "program_id": cls.program.id,
        })
        cls.plan = cls.Plan.create({
            "name": "Workflow Visibility Plan",
            "price": 100,
            "program_ids": [(6, 0, cls.program.ids)],
        })
        cls.subscription_stage = cls.env["sale.subscription.stage"].search(
            [("type", "=", "in_progress")],
            limit=1,
        )

    def _member(self, name, membership_state="active"):
        return self.Member.with_context(
            mail_create_nolog=True,
            tracking_disable=True,
        ).create({
            "name": name,
            "email": "%s@example.com" % name.lower().replace(" ", "."),
            "membership_state": membership_state,
        })

    def _subscription(self, member):
        return self.Subscription.create({
            "member_id": member.id,
            "plan_id": self.plan.id,
            "pricelist_id": self.pricelist.id,
            "stage_id": self.subscription_stage.id,
        })

    def _session(self, member=None, start=None):
        start = start or fields.Datetime.now()
        session = self.ClassSession.create({
            "template_id": self.template.id,
            "start_datetime": start,
            "end_datetime": start + timedelta(minutes=60),
            "state": "open",
            "capacity": 20,
        })
        if member:
            self.Enrollment.create({
                "session_id": session.id,
                "member_id": member.id,
                "status": "registered",
            })
        return session

    def _instructor_task(self, member):
        project = self.env.ref(
            "dojo_core.project_instructor_alerts",
            raise_if_not_found=False,
        )
        stage = self.env.ref(
            "dojo_core.stage_instructor_todo",
            raise_if_not_found=False,
        )
        if not project or not stage:
            self.skipTest("Instructor Alerts project data is not installed")
        return self.Task.sudo().create({
            "name": "Visibility follow-up: %s" % member.name,
            "project_id": project.id,
            "stage_id": stage.id,
            "date_deadline": fields.Date.today(),
        })

    def test_roster_payload_contains_compact_workflow_status_and_tasks(self):
        member = self._member("Roster Visibility Student")
        self._subscription(member)
        session = self._session(member)
        self._instructor_task(member)

        roster = self.KioskService.get_session_roster(session.id)
        entry = next(item for item in roster if item.get("member_id") == member.id)
        workflow = entry["workflow_status"]

        self.assertIn("onboarding", workflow)
        self.assertIn("waiver", workflow)
        self.assertIn("subscription", workflow)
        self.assertIn("attendance", workflow)
        self.assertIn("grading", workflow)
        self.assertIn("tasks", workflow)
        self.assertEqual(entry["issues"], workflow["alerts"])
        self.assertEqual(workflow["subscription"]["state"], "active")
        self.assertGreaterEqual(workflow["tasks"]["open_count"], 1)
        self.assertEqual(workflow["tasks"]["tasks"], [])

    def test_profile_payload_contains_attendance_belt_program_and_full_tasks(self):
        member = self._member("Profile Visibility Student")
        self._subscription(member)
        current_rank = self.BeltRank.create({
            "name": "Visibility White Belt",
            "sequence": -9000,
            "color": "#ffffff",
        })
        next_rank = self.BeltRank.create({
            "name": "Visibility Yellow Belt",
            "sequence": -8999,
            "color": "#facc15",
            "attendance_threshold": 2,
        })
        self.MemberRank.create({
            "member_id": member.id,
            "rank_id": current_rank.id,
            "program_id": self.program.id,
            "date_awarded": fields.Date.today(),
        })
        first_session = self._session(member, fields.Datetime.now() - timedelta(days=1))
        second_session = self._session(member, fields.Datetime.now())
        for session in (first_session, second_session):
            self.AttendanceLog.create({
                "session_id": session.id,
                "member_id": member.id,
                "status": "present",
            })
        self._instructor_task(member)
        member.invalidate_recordset()

        profile = self.KioskService.get_member_profile(member.id, session_id=second_session.id)
        workflow = profile["workflow_status"]
        program_rows = {
            row["program_id"]: row
            for row in profile["programs"]
        }

        self.assertEqual(profile["belt_rank"], current_rank.name)
        self.assertEqual(workflow["attendance"]["total"], 2)
        self.assertEqual(workflow["attendance"]["since_last_rank"], 2)
        self.assertEqual(workflow["grading"]["next_rank"]["id"], next_rank.id)
        self.assertTrue(workflow["grading"]["ready"])
        self.assertEqual(program_rows[self.program.id]["rank_name"], current_rank.name)
        self.assertEqual(program_rows[self.program.id]["attendance_count"], 2)
        self.assertGreaterEqual(workflow["tasks"]["open_count"], 1)
        self.assertTrue(workflow["tasks"]["tasks"])

    def test_optional_onboarding_and_waiver_statuses_when_sources_installed(self):
        member = self._member("Optional Workflow Student")
        checked_any_source = False

        if "dojo.onboarding.record" in self.env:
            checked_any_source = True
            self.env["dojo.onboarding.record"].create({
                "member_id": member.id,
                "company_id": member.company_id.id,
                "step_member_info": True,
                "step_household": True,
            })
            onboarding = self.KioskService._member_onboarding_status(member)
            self.assertTrue(onboarding["available"])
            self.assertFalse(onboarding["complete"])
            self.assertEqual(onboarding["progress_pct"], 40)
            self.assertIn("Subscription", onboarding["missing_steps"])

        if "has_signed_waiver" in member._fields:
            checked_any_source = True
            waiver = self.KioskService._member_waiver_status(member)
            self.assertTrue(waiver["available"])
            self.assertFalse(waiver["signed"])

            member.sudo().write({
                "waiver_signed_by": "Workflow Guardian",
                "waiver_signed_on": fields.Datetime.now(),
            })
            member.invalidate_recordset()
            waiver = self.KioskService._member_waiver_status(member)
            self.assertTrue(waiver["signed"])
            self.assertEqual(waiver["signed_by"], "Workflow Guardian")

        if not checked_any_source:
            self.skipTest("Optional onboarding and waiver modules are not installed")
