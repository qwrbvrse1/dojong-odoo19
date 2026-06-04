from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestKioskSessionContext(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.KioskService = cls.env["dojo.kiosk.service"]
        cls.Program = cls.env["dojo.program"]
        cls.ClassTemplate = cls.env["dojo.class.template"]
        cls.ClassSession = cls.env["dojo.class.session"]
        cls.Member = cls.env["dojo.member"]
        cls.Plan = cls.env["dojo.subscription.plan"]
        cls.Subscription = cls.env["sale.subscription"]

    def _payload(self, session_id, start, end, state="open", name="Class"):
        return {
            "id": session_id,
            "name": name,
            "template_name": name,
            "state": state,
            "start": fields.Datetime.to_string(start),
            "end": fields.Datetime.to_string(end),
        }

    def test_active_session_is_selected_first(self):
        now = fields.Datetime.now()
        active = self._payload(1, now - timedelta(minutes=10), now + timedelta(minutes=40), name="Active")
        upcoming = self._payload(2, now + timedelta(minutes=5), now + timedelta(minutes=65), name="Upcoming")

        ctx = self.KioskService.get_session_context_from_payload([upcoming, active], now=now)

        self.assertEqual(ctx["mode"], "active")
        self.assertEqual(ctx["selected_session_id"], 1)

    def test_overlapping_active_sessions_use_deterministic_fallback(self):
        now = fields.Datetime.now()
        first = self._payload(1, now - timedelta(minutes=20), now + timedelta(minutes=10), name="First")
        second = self._payload(2, now - timedelta(minutes=5), now + timedelta(minutes=55), name="Second")

        ctx = self.KioskService.get_session_context_from_payload([second, first], now=now)

        self.assertEqual(ctx["mode"], "active")
        self.assertEqual(ctx["selected_session_id"], 1)

    def test_nearest_upcoming_session_within_threshold_is_selected(self):
        now = fields.Datetime.now()
        later = self._payload(1, now + timedelta(minutes=14), now + timedelta(minutes=74), name="Later")
        soonest = self._payload(2, now + timedelta(minutes=4), now + timedelta(minutes=64), name="Soonest")

        ctx = self.KioskService.get_session_context_from_payload([later, soonest], now=now)

        self.assertEqual(ctx["mode"], "upcoming")
        self.assertEqual(ctx["selected_session_id"], 2)

    def test_completed_in_progress_session_is_not_selected(self):
        now = fields.Datetime.now()
        completed = self._payload(1, now - timedelta(minutes=10), now + timedelta(minutes=40), state="done", name="Done")
        upcoming = self._payload(2, now + timedelta(minutes=4), now + timedelta(minutes=64), name="Upcoming")

        ctx = self.KioskService.get_session_context_from_payload([completed, upcoming], now=now)

        self.assertEqual(ctx["mode"], "upcoming")
        self.assertEqual(ctx["selected_session_id"], 2)

    def test_standby_when_no_relevant_session(self):
        now = fields.Datetime.now()
        future = self._payload(1, now + timedelta(minutes=30), now + timedelta(minutes=90), name="Future")

        ctx = self.KioskService.get_session_context_from_payload([future], now=now)

        self.assertEqual(ctx["mode"], "standby")
        self.assertFalse(ctx["selected_session_id"])

    def test_selected_active_session_accepts_checkin_and_roster_loading(self):
        now = fields.Datetime.now()
        program = self.Program.create({"name": "Kiosk Context Program"})
        template = self.ClassTemplate.create({
            "name": "Kiosk Context Course",
            "program_id": program.id,
        })
        session = self.ClassSession.create({
            "template_id": template.id,
            "start_datetime": now - timedelta(minutes=5),
            "end_datetime": now + timedelta(minutes=55),
            "state": "open",
            "capacity": 20,
        })
        member = self.Member.with_context(
            mail_create_nolog=True,
            tracking_disable=True,
        ).create({
            "name": "Kiosk Context Student",
            "membership_state": "active",
        })
        self._active_subscription(member, program)

        ctx = self.KioskService.get_session_context_from_payload(
            [self.KioskService._session_payload(session)],
            now=fields.Datetime.to_string(now),
        )
        result = self.KioskService.checkin_member(member.id, ctx["selected_session_id"])
        roster = self.KioskService.get_session_roster(session.id)

        self.assertEqual(ctx["mode"], "active")
        self.assertTrue(result["success"], result.get("error"))
        self.assertIn(member.id, {entry.get("member_id") for entry in roster})

    def _active_subscription(self, member, program):
        pricelist = self.env["product.pricelist"].search([], limit=1)
        if not pricelist:
            pricelist = self.env["product.pricelist"].create({
                "name": "Kiosk Context Pricelist",
                "currency_id": self.env.company.currency_id.id,
            })
        stage = self.env["sale.subscription.stage"].search(
            [("type", "=", "in_progress")],
            limit=1,
        )
        plan = self.Plan.create({
            "name": "Kiosk Context Plan",
            "price": 100,
            "program_ids": [(6, 0, program.ids)],
        })
        return self.Subscription.create({
            "member_id": member.id,
            "plan_id": plan.id,
            "pricelist_id": pricelist.id,
            "stage_id": stage.id,
        })
