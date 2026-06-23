from datetime import datetime, timedelta

from odoo.tests.common import TransactionCase


class TestAnalyticsController(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create test data
        cls.Member = cls.env['dojo.member']
        cls.AttendanceLog = cls.env['dojo.attendance.log']
        cls.ClassSession = cls.env['dojo.class.session']
        cls.ClassTemplate = cls.env['dojo.class.template']
        cls.BeltRank = cls.env['dojo.belt.rank']

        # Create belt rank
        cls.belt_white = cls.BeltRank.create({
            'name': 'White Belt',
            'sequence': 1,
            'color': '#FFFFFF',
        })

        # Create members
        cls.member_active = cls.Member.create({
            'name': 'Active Member',
            'membership_state': 'active',
            'current_rank_id': cls.belt_white.id,
        })

        cls.member_inactive = cls.Member.create({
            'name': 'Inactive Member',
            'membership_state': 'active',
            'current_rank_id': cls.belt_white.id,
        })

        # Create class template
        cls.template = cls.ClassTemplate.create({
            'name': 'Test Class',
        })

        # Create sessions
        now = datetime.now()
        cls.session_1 = cls.ClassSession.create({
            'template_id': cls.template.id,
            'start_datetime': now - timedelta(days=5),
            'end_datetime': now - timedelta(days=5, hours=-1),
            'state': 'done',
        })

        cls.session_2 = cls.ClassSession.create({
            'template_id': cls.template.id,
            'start_datetime': now - timedelta(days=10),
            'end_datetime': now - timedelta(days=10, hours=-1),
            'state': 'done',
        })

        # Create attendance logs for active member
        cls.log_1 = cls.AttendanceLog.create({
            'session_id': cls.session_1.id,
            'member_id': cls.member_active.id,
            'status': 'present',
            'checkin_datetime': now - timedelta(days=5),
        })

        cls.log_2 = cls.AttendanceLog.create({
            'session_id': cls.session_2.id,
            'member_id': cls.member_active.id,
            'status': 'present',
            'checkin_datetime': now - timedelta(days=10),
        })

        # Create old attendance log for inactive member (45 days ago)
        cls.old_session = cls.ClassSession.create({
            'template_id': cls.template.id,
            'start_datetime': now - timedelta(days=45),
            'end_datetime': now - timedelta(days=45, hours=-1),
            'state': 'done',
        })

        cls.log_old = cls.AttendanceLog.create({
            'session_id': cls.old_session.id,
            'member_id': cls.member_inactive.id,
            'status': 'present',
            'checkin_datetime': now - timedelta(days=45),
        })

    def test_analytics_returns_expected_keys(self):
        """Test that analytics controller returns all expected keys"""
        from odoo.addons.dojo_instructor_dashboard.controllers.analytics import InstructorAnalyticsController

        controller = InstructorAnalyticsController()
        result = controller._compute_analytics_data(self.env, days=30)

        self.assertIn('busiest_sessions', result)
        self.assertIn('top_attending_members', result)
        self.assertIn('inactive_members', result)
        self.assertIn('period_days', result)
        self.assertEqual(result['period_days'], 30)

    def test_inactive_list_excludes_members_with_recent_attendance(self):
        """Test that inactive members list excludes members with recent attendance"""
        from odoo.addons.dojo_instructor_dashboard.controllers.analytics import InstructorAnalyticsController

        controller = InstructorAnalyticsController()
        result = controller._compute_analytics_data(self.env, days=30)

        # Active member should NOT be in inactive list
        inactive_member_ids = [m['member_id'] for m in result['inactive_members']]
        self.assertNotIn(self.member_active.id, inactive_member_ids)

        # Inactive member should be in inactive list (last attendance was 45 days ago)
        self.assertIn(self.member_inactive.id, inactive_member_ids)

    def test_busiest_sessions_includes_recent_sessions(self):
        """Test that busiest sessions includes sessions with attendance in the period"""
        from odoo.addons.dojo_instructor_dashboard.controllers.analytics import InstructorAnalyticsController

        controller = InstructorAnalyticsController()
        result = controller._compute_analytics_data(self.env, days=30)

        # Should have sessions from last 30 days
        session_ids = [s['session_id'] for s in result['busiest_sessions']]
        self.assertIn(self.session_1.id, session_ids)
        self.assertIn(self.session_2.id, session_ids)

        # Old session (45 days ago) should not be included
        self.assertNotIn(self.old_session.id, session_ids)

    def test_top_attending_members_ranks_by_checkin_count(self):
        """Test that top attending members are ranked by check-in count"""
        from odoo.addons.dojo_instructor_dashboard.controllers.analytics import InstructorAnalyticsController

        controller = InstructorAnalyticsController()
        result = controller._compute_analytics_data(self.env, days=30)

        # Active member should be in top attending list
        member_ids = [m['member_id'] for m in result['top_attending_members']]
        self.assertIn(self.member_active.id, member_ids)

        # Find the active member's entry
        active_entry = next((m for m in result['top_attending_members'] if m['member_id'] == self.member_active.id), None)
        self.assertIsNotNone(active_entry)
        self.assertEqual(active_entry['checkin_count'], 2)  # Two check-ins in last 30 days
