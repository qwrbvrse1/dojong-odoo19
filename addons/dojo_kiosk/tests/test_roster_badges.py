"""Test onboarding progress and task badges on instructor roster tiles."""
from odoo.tests.common import TransactionCase


class TestRosterBadges(TransactionCase):
    """Verify roster entries include onboarding_pct and open_task_count."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.KioskService = cls.env["dojo.kiosk.service"]
        cls.Member = cls.env["dojo.member"]
        cls.Session = cls.env["dojo.class.session"]
        cls.Template = cls.env["dojo.class.template"]
        cls.Enrollment = cls.env["dojo.class.enrollment"]

        # Create a program and subscription plan
        cls.program = cls.env["dojo.program"].create({"name": "Badge Test Program"})
        cls.plan = cls.env["dojo.subscription.plan"].create({
            "name": "Test Badge Plan",
            "price": 100.00,
            "credits_per_period": 12,
            "program_ids": [(6, 0, cls.program.ids)],
        })

        # Create a class template and session linked to the program
        cls.template = cls.Template.create({
            "name": "Badge Test Class",
            "program_id": cls.program.id,
        })
        cls.session = cls.Session.create({
            "name": "Badge Test Session",
            "template_id": cls.template.id,
            "start_datetime": "2026-06-22 10:00:00",
            "end_datetime": "2026-06-22 11:00:00",
        })

        # Create pricelist if none exists
        cls.pricelist = cls.env["product.pricelist"].search([], limit=1)
        if not cls.pricelist:
            cls.pricelist = cls.env["product.pricelist"].create({
                "name": "Test Pricelist",
                "currency_id": cls.env.company.currency_id.id,
            })
        cls.active_stage = cls.env["sale.subscription.stage"].search(
            [("type", "=", "in_progress")],
            limit=1,
        )

    def _create_active_subscription(self, member):
        """Create an active subscription for a member to satisfy enrollment constraints."""
        return self.env["sale.subscription"].create({
            "partner_id": member.partner_id.id,
            "member_id": member.id,
            "plan_id": self.plan.id,
            "pricelist_id": self.pricelist.id,
            "stage_id": self.active_stage.id,
        })

    def test_roster_entry_includes_onboarding_pct_when_incomplete(self):
        """Roster entry includes onboarding_pct when progress < 100."""
        member = self.Member.create({"name": "Incomplete Onboarding Student"})
        self._create_active_subscription(member)
        # Create onboarding record with 2/5 steps complete (40%)
        if "dojo.onboarding.record" in self.env:
            self.env["dojo.onboarding.record"].create({
                "member_id": member.id,
                "step_member_info": True,
                "step_household": True,
                "step_enrollment": False,
                "step_subscription": False,
                "step_portal_access": False,
            })
        self.Enrollment.create({
            "session_id": self.session.id,
            "member_id": member.id,
            "status": "registered",
        })
        roster = self.KioskService.get_session_roster(self.session.id)
        entry = next((r for r in roster if r["member_id"] == member.id), None)
        self.assertIsNotNone(entry)
        if "dojo.onboarding.record" in self.env:
            self.assertEqual(entry["onboarding_pct"], 40)
        else:
            # When module not installed, onboarding_pct should be 0
            self.assertEqual(entry["onboarding_pct"], 0)

    def test_roster_entry_includes_onboarding_pct_zero_when_complete(self):
        """Roster entry sets onboarding_pct to 0 when complete (100%)."""
        member = self.Member.create({"name": "Complete Onboarding Student"})
        self._create_active_subscription(member)
        if "dojo.onboarding.record" in self.env:
            self.env["dojo.onboarding.record"].create({
                "member_id": member.id,
                "step_member_info": True,
                "step_household": True,
                "step_enrollment": True,
                "step_subscription": True,
                "step_portal_access": True,
            })
        self.Enrollment.create({
            "session_id": self.session.id,
            "member_id": member.id,
            "status": "registered",
        })
        roster = self.KioskService.get_session_roster(self.session.id)
        entry = next((r for r in roster if r["member_id"] == member.id), None)
        self.assertIsNotNone(entry)
        # Complete onboarding (100%) is represented as 0 in roster payload
        self.assertEqual(entry["onboarding_pct"], 0)

    def test_roster_entry_includes_open_task_count_when_tasks_exist(self):
        """Roster entry includes open_task_count when instructor tasks exist."""
        member = self.Member.create({"name": "Student With Tasks"})
        self._create_active_subscription(member)
        if "project.task" in self.env:
            Task = self.env["project.task"]
            # Use the dojo_core instructor alerts project if available
            project = self.env.ref(
                "dojo_core.project_instructor_alerts",
                raise_if_not_found=False,
            )
            stage = self.env.ref(
                "dojo_core.stage_instructor_todo",
                raise_if_not_found=False,
            )
            if project and stage:
                Task.create({
                    "name": member.name + " - Follow up required",
                    "project_id": project.id,
                    "stage_id": stage.id,
                })
                Task.create({
                    "name": member.name + " - Billing issue",
                    "project_id": project.id,
                    "stage_id": stage.id,
                })
            else:
                # Fallback: create without project (will match all)
                Project = self.env["project.project"]
                Stage = self.env["project.task.type"]
                open_stage = Stage.create({"name": "Open", "fold": False})
                Task.create({
                    "name": member.name + " - Follow up required",
                    "stage_id": open_stage.id,
                })
                Task.create({
                    "name": member.name + " - Billing issue",
                    "stage_id": open_stage.id,
                })
        self.Enrollment.create({
            "session_id": self.session.id,
            "member_id": member.id,
            "status": "registered",
        })
        roster = self.KioskService.get_session_roster(self.session.id)
        entry = next((r for r in roster if r["member_id"] == member.id), None)
        self.assertIsNotNone(entry)
        if "project.task" in self.env:
            self.assertEqual(entry["open_task_count"], 2)
        else:
            self.assertEqual(entry["open_task_count"], 0)

    def test_roster_entry_includes_open_task_count_zero_when_no_tasks(self):
        """Roster entry sets open_task_count to 0 when no tasks exist."""
        member = self.Member.create({"name": "Student Without Tasks"})
        self._create_active_subscription(member)
        self.Enrollment.create({
            "session_id": self.session.id,
            "member_id": member.id,
            "status": "registered",
        })
        roster = self.KioskService.get_session_roster(self.session.id)
        entry = next((r for r in roster if r["member_id"] == member.id), None)
        self.assertIsNotNone(entry)
        self.assertEqual(entry["open_task_count"], 0)

    def test_session_roster_returns_all_badges(self):
        """Session roster includes both badges across multiple members."""
        m1 = self.Member.create({"name": "Badge Combo One"})
        m2 = self.Member.create({"name": "Badge Combo Two"})
        self._create_active_subscription(m1)
        self._create_active_subscription(m2)
        if "dojo.onboarding.record" in self.env:
            self.env["dojo.onboarding.record"].create({
                "member_id": m1.id,
                "step_member_info": True,
                "step_household": False,
                "step_enrollment": False,
                "step_subscription": False,
                "step_portal_access": False,
            })
        if "project.task" in self.env:
            Project = self.env["project.project"]
            Task = self.env["project.task"]
            Stage = self.env["project.task.type"]
            project = Project.create({"name": "Instructor Alerts 2"})
            open_stage = Stage.create({"name": "Open2", "fold": False})
            Task.create({
                "name": m2.name + " - Task",
                "project_id": project.id,
                "stage_id": open_stage.id,
            })
        self.Enrollment.create({
            "session_id": self.session.id,
            "member_id": m1.id,
            "status": "registered",
        })
        self.Enrollment.create({
            "session_id": self.session.id,
            "member_id": m2.id,
            "status": "registered",
        })
        roster = self.KioskService.get_session_roster(self.session.id)
        e1 = next((r for r in roster if r["member_id"] == m1.id), None)
        e2 = next((r for r in roster if r["member_id"] == m2.id), None)
        self.assertIsNotNone(e1)
        self.assertIsNotNone(e2)
        self.assertIn("onboarding_pct", e1)
        self.assertIn("open_task_count", e1)
        self.assertIn("onboarding_pct", e2)
        self.assertIn("open_task_count", e2)
