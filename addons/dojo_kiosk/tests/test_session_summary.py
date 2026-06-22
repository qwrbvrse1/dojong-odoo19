"""Test session summary service method for instructor three-panel layout."""
from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSessionSummary(TransactionCase):
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
        cls.Plan = cls.env["dojo.subscription.plan"]
        cls.Subscription = cls.env["sale.subscription"]
        cls.pricelist = cls.env["product.pricelist"].search([], limit=1)
        if not cls.pricelist:
            cls.pricelist = cls.env["product.pricelist"].create({
                "name": "Test Pricelist",
                "currency_id": cls.env.company.currency_id.id,
            })
        cls.subscription_stage = cls.env["sale.subscription.stage"].search(
            [("type", "=", "in_progress")],
            limit=1,
        )
        cls.program = cls.Program.create({"name": "Session Summary Test Program"})
        cls.template = cls.ClassTemplate.create({
            "name": "Session Summary Test Course",
            "program_id": cls.program.id,
        })
        cls.plan = cls.Plan.create({
            "name": "Test Plan",
            "price": 100,
            "program_ids": [(6, 0, cls.program.ids)],
        })

    def _member(self, name):
        member = self.Member.with_context(
            mail_create_nolog=True,
            tracking_disable=True,
        ).create({
            "name": name,
            "email": "%s@example.com" % name.lower().replace(" ", "."),
            "membership_state": "active",
        })
        self.Subscription.create({
            "member_id": member.id,
            "plan_id": self.plan.id,
            "pricelist_id": self.pricelist.id,
            "stage_id": self.subscription_stage.id,
        })
        return member

    def _session_with_attendance(self, present_count, late_count, absent_count):
        start = fields.Datetime.now() - timedelta(minutes=30)
        session = self.ClassSession.create({
            "template_id": self.template.id,
            "start_datetime": start,
            "end_datetime": start + timedelta(minutes=60),
            "state": "open",
            "capacity": 20,
        })
        for i in range(present_count):
            member = self._member("Present Student %d" % i)
            self.Enrollment.create({
                "session_id": session.id,
                "member_id": member.id,
                "status": "registered",
            })
            self.AttendanceLog.create({
                "session_id": session.id,
                "member_id": member.id,
                "status": "present",
            })
        for i in range(late_count):
            member = self._member("Late Student %d" % i)
            self.Enrollment.create({
                "session_id": session.id,
                "member_id": member.id,
                "status": "registered",
            })
            self.AttendanceLog.create({
                "session_id": session.id,
                "member_id": member.id,
                "status": "late",
            })
        for i in range(absent_count):
            member = self._member("Absent Student %d" % i)
            self.Enrollment.create({
                "session_id": session.id,
                "member_id": member.id,
                "status": "registered",
            })
            self.AttendanceLog.create({
                "session_id": session.id,
                "member_id": member.id,
                "status": "absent",
            })
        return session

    def test_get_session_summary_returns_counts(self):
        """get_session_summary returns present, late, and absent counts."""
        session = self._session_with_attendance(present_count=3, late_count=2, absent_count=1)
        summary = self.KioskService.get_session_summary(session.id)

        self.assertTrue(summary.get("success"))
        self.assertEqual(summary["present_count"], 3)
        self.assertEqual(summary["late_count"], 2)
        self.assertEqual(summary["absent_count"], 1)
        self.assertEqual(summary["total_enrolled"], 6)

    def test_get_session_summary_returns_session_info(self):
        """get_session_summary returns session details for the countdown timer."""
        start = fields.Datetime.now() - timedelta(minutes=15)
        end = start + timedelta(minutes=60)
        session = self.ClassSession.create({
            "template_id": self.template.id,
            "start_datetime": start,
            "end_datetime": end,
            "state": "open",
            "capacity": 20,
        })

        summary = self.KioskService.get_session_summary(session.id)

        self.assertTrue(summary.get("success"))
        self.assertEqual(summary["session_id"], session.id)
        self.assertEqual(summary["session_name"], session.name)
        self.assertEqual(summary["start_datetime"], fields.Datetime.to_string(start))
        self.assertEqual(summary["end_datetime"], fields.Datetime.to_string(end))
        self.assertEqual(summary["template_name"], self.template.name)
