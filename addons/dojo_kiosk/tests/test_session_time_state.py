"""Tests for time_state field on session list."""
from datetime import datetime, timedelta
from odoo.tests.common import TransactionCase
from odoo import fields


class TestSessionTimeState(TransactionCase):
    """Verify get_todays_sessions() returns time_state on each session dict."""

    def setUp(self):
        super().setUp()
        self.Service = self.env["dojo.kiosk.service"]

        # Create a template
        self.template = self.env["dojo.class.template"].create({
            "name": "Test Class Template",
            "duration_minutes": 60,
        })

    def test_active_session_time_state(self):
        """Session that is currently active should have time_state='active'."""
        now = fields.Datetime.now()
        start = now - timedelta(minutes=10)
        end = now + timedelta(minutes=50)

        session = self.env["dojo.class.session"].create({
            "template_id": self.template.id,
            "start_datetime": start,
            "end_datetime": end,
            "state": "open",
        })

        sessions = self.Service.get_todays_sessions()
        session_dict = next((s for s in sessions if s["id"] == session.id), None)
        self.assertIsNotNone(session_dict)
        self.assertEqual(session_dict["time_state"], "active")

    def test_done_session_time_state(self):
        """Session that ended should have time_state='done'."""
        now = fields.Datetime.now()
        start = now - timedelta(hours=2)
        end = now - timedelta(hours=1)

        session = self.env["dojo.class.session"].create({
            "template_id": self.template.id,
            "start_datetime": start,
            "end_datetime": end,
            "state": "open",
        })

        sessions = self.Service.get_todays_sessions()
        session_dict = next((s for s in sessions if s["id"] == session.id), None)
        self.assertIsNotNone(session_dict)
        self.assertEqual(session_dict["time_state"], "done")

    def test_upcoming_soon_session_time_state(self):
        """Session starting within 15 minutes should have time_state='upcoming_soon'."""
        now = fields.Datetime.now()
        start = now + timedelta(minutes=10)
        end = start + timedelta(minutes=60)

        session = self.env["dojo.class.session"].create({
            "template_id": self.template.id,
            "start_datetime": start,
            "end_datetime": end,
            "state": "open",
        })

        sessions = self.Service.get_todays_sessions()
        session_dict = next((s for s in sessions if s["id"] == session.id), None)
        self.assertIsNotNone(session_dict)
        self.assertEqual(session_dict["time_state"], "upcoming_soon")

    def test_upcoming_session_time_state(self):
        """Session starting more than 15 minutes away should have time_state='upcoming'."""
        now = fields.Datetime.now()
        start = now + timedelta(minutes=30)
        end = start + timedelta(minutes=60)

        session = self.env["dojo.class.session"].create({
            "template_id": self.template.id,
            "start_datetime": start,
            "end_datetime": end,
            "state": "open",
        })

        sessions = self.Service.get_todays_sessions()
        session_dict = next((s for s in sessions if s["id"] == session.id), None)
        self.assertIsNotNone(session_dict)
        self.assertEqual(session_dict["time_state"], "upcoming")

    def test_boundary_upcoming_soon_exactly_15_minutes(self):
        """Session starting exactly 15 minutes away should be 'upcoming_soon'."""
        now = fields.Datetime.now()
        start = now + timedelta(minutes=15)
        end = start + timedelta(minutes=60)

        session = self.env["dojo.class.session"].create({
            "template_id": self.template.id,
            "start_datetime": start,
            "end_datetime": end,
            "state": "open",
        })

        sessions = self.Service.get_todays_sessions()
        session_dict = next((s for s in sessions if s["id"] == session.id), None)
        self.assertIsNotNone(session_dict)
        self.assertEqual(session_dict["time_state"], "upcoming_soon")

    def test_boundary_upcoming_just_after_15_minutes(self):
        """Session starting 16 minutes away should be 'upcoming'."""
        now = fields.Datetime.now()
        start = now + timedelta(minutes=16)
        end = start + timedelta(minutes=60)

        session = self.env["dojo.class.session"].create({
            "template_id": self.template.id,
            "start_datetime": start,
            "end_datetime": end,
            "state": "open",
        })

        sessions = self.Service.get_todays_sessions()
        session_dict = next((s for s in sessions if s["id"] == session.id), None)
        self.assertIsNotNone(session_dict)
        self.assertEqual(session_dict["time_state"], "upcoming")

    def test_multiple_sessions_different_time_states(self):
        """Multiple sessions should each have their own correct time_state."""
        now = fields.Datetime.now()

        # Active session
        active = self.env["dojo.class.session"].create({
            "template_id": self.template.id,
            "start_datetime": now - timedelta(minutes=10),
            "end_datetime": now + timedelta(minutes=50),
            "state": "open",
        })

        # Done session
        done = self.env["dojo.class.session"].create({
            "template_id": self.template.id,
            "start_datetime": now - timedelta(hours=2),
            "end_datetime": now - timedelta(hours=1),
            "state": "open",
        })

        # Upcoming soon
        soon = self.env["dojo.class.session"].create({
            "template_id": self.template.id,
            "start_datetime": now + timedelta(minutes=10),
            "end_datetime": now + timedelta(minutes=70),
            "state": "open",
        })

        # Upcoming
        upcoming = self.env["dojo.class.session"].create({
            "template_id": self.template.id,
            "start_datetime": now + timedelta(minutes=30),
            "end_datetime": now + timedelta(minutes=90),
            "state": "open",
        })

        sessions = self.Service.get_todays_sessions()

        active_dict = next((s for s in sessions if s["id"] == active.id), None)
        self.assertEqual(active_dict["time_state"], "active")

        done_dict = next((s for s in sessions if s["id"] == done.id), None)
        self.assertEqual(done_dict["time_state"], "done")

        soon_dict = next((s for s in sessions if s["id"] == soon.id), None)
        self.assertEqual(soon_dict["time_state"], "upcoming_soon")

        upcoming_dict = next((s for s in sessions if s["id"] == upcoming.id), None)
        self.assertEqual(upcoming_dict["time_state"], "upcoming")
