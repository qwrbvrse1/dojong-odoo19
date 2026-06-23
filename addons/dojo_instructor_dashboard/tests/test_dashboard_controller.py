from datetime import date, timedelta

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestDashboardController(TransactionCase):
    """Test suite for instructor dashboard controller endpoint."""

    def test_dashboard_data_structure(self):
        """Test that dashboard data endpoint returns correct structure."""
        from odoo.addons.dojo_instructor_dashboard.controllers.dashboard import InstructorDashboardController

        controller = InstructorDashboardController()
        data = controller._compute_dashboard_data(self.env)

        # Check all required keys are present
        required_keys = [
            'active_students',
            'todays_checkins',
            'upcoming_birthdays',
            'expiring_memberships',
            'belt_distribution',
            'birthday_list',
            'expiring_list',
        ]
        for key in required_keys:
            self.assertIn(key, data)

        # Check data types
        self.assertIsInstance(data['active_students'], int)
        self.assertIsInstance(data['todays_checkins'], int)
        self.assertIsInstance(data['upcoming_birthdays'], int)
        self.assertIsInstance(data['expiring_memberships'], int)
        self.assertIsInstance(data['belt_distribution'], list)
        self.assertIsInstance(data['birthday_list'], list)
        self.assertIsInstance(data['expiring_list'], list)

    def test_active_students_count(self):
        """Test active students count in dashboard data."""
        from odoo.addons.dojo_instructor_dashboard.controllers.dashboard import InstructorDashboardController

        # Create active and inactive members
        self.env['dojo.member'].create({
            'name': 'Active Member 1',
            'membership_state': 'active',
        })
        self.env['dojo.member'].create({
            'name': 'Active Member 2',
            'membership_state': 'active',
        })
        self.env['dojo.member'].create({
            'name': 'Cancelled Member',
            'membership_state': 'cancelled',
        })

        controller = InstructorDashboardController()
        data = controller._compute_dashboard_data(self.env)

        self.assertGreaterEqual(data['active_students'], 2)

    def test_upcoming_birthdays(self):
        """Test upcoming birthdays calculation (year-agnostic)."""
        from odoo.addons.dojo_instructor_dashboard.controllers.dashboard import InstructorDashboardController

        # Create member with birthday in 3 days
        in_three_days = date.today() + timedelta(days=3)
        # Use a past year to ensure year-agnostic matching
        past_year_birthday = in_three_days.replace(year=1990)

        self.env['dojo.member'].create({
            'name': 'Birthday Member',
            'membership_state': 'active',
            'date_of_birth': past_year_birthday,
        })

        controller = InstructorDashboardController()
        data = controller._compute_dashboard_data(self.env)

        self.assertGreaterEqual(data['upcoming_birthdays'], 1)
        # Check birthday_list contains the member
        birthday_names = [b['name'] for b in data['birthday_list']]
        self.assertIn('Birthday Member', birthday_names)

    def test_expiring_memberships(self):
        """Test expiring memberships list."""
        from odoo.addons.dojo_instructor_dashboard.controllers.dashboard import InstructorDashboardController

        # Create member with expdate in 15 days
        in_fifteen_days = date.today() + timedelta(days=15)

        member = self.env['dojo.member'].create({
            'name': 'Expiring Member',
            'membership_state': 'active',
        })
        # Manually set expdate (computed field)
        member.write({'expdate': in_fifteen_days})

        controller = InstructorDashboardController()
        data = controller._compute_dashboard_data(self.env)

        self.assertGreaterEqual(data['expiring_memberships'], 1)
        # Check expiring_list contains the member
        expiring_names = [e['name'] for e in data['expiring_list']]
        self.assertIn('Expiring Member', expiring_names)

    def test_belt_distribution(self):
        """Test belt distribution chart data."""
        from odoo.addons.dojo_instructor_dashboard.controllers.dashboard import InstructorDashboardController

        # Create test belt rank
        white_belt = self.env['dojo.belt.rank'].create({
            'name': 'White Belt',
            'sequence': 10,
            'color': '#ffffff',
        })

        # Create member with belt rank using the proper way
        member = self.env['dojo.member'].create({
            'name': 'White Belt Member',
            'membership_state': 'active',
        })

        # Create rank history record
        self.env['dojo.member.rank'].create({
            'member_id': member.id,
            'rank_id': white_belt.id,
        })

        # Create unranked member
        self.env['dojo.member'].create({
            'name': 'Unranked Member',
            'membership_state': 'active',
        })

        controller = InstructorDashboardController()
        data = controller._compute_dashboard_data(self.env)

        self.assertTrue(len(data['belt_distribution']) > 0)
        # Check that belt names and counts are present
        belt_ranks = [b['rank'] for b in data['belt_distribution']]
        self.assertIn('Unranked', belt_ranks)
