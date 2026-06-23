from datetime import datetime, timedelta
from odoo.tests.common import TransactionCase


class TestDojoMemberReports(TransactionCase):

    def setUp(self):
        super().setUp()

        # Create test members
        self.member_active = self.env['dojo.member'].create({
            'name': 'Active Member',
            'email': 'active@example.com',
            'phone': '555-0001',
            'membership_state': 'active',
        })

        self.member_no_contact = self.env['dojo.member'].create({
            'name': 'No Contact Member',
            'membership_state': 'active',
        })

        # Create a household
        self.household = self.env['res.partner'].create({
            'name': 'Test Family',
            'is_household': True,
            'is_company': True,
        })

        self.member_family_1 = self.env['dojo.member'].create({
            'name': 'Family Member 1',
            'email': 'family1@example.com',
            'phone': '555-0002',
            'membership_state': 'active',
        })
        self.member_family_1.partner_id.parent_id = self.household

        self.member_family_2 = self.env['dojo.member'].create({
            'name': 'Family Member 2',
            'email': 'family2@example.com',
            'phone': '555-0003',
            'membership_state': 'active',
        })
        self.member_family_2.partner_id.parent_id = self.household

    def test_member_missing_contact_info(self):
        """Test that members missing contact info can be identified."""
        # member_no_contact should be missing both email and phone
        self.assertFalse(self.member_no_contact.email)
        self.assertFalse(self.member_no_contact.phone)

        # member_active should have contact info
        self.assertTrue(self.member_active.email)
        self.assertTrue(self.member_active.phone)

    def test_household_grouping(self):
        """Test that members can be grouped by household."""
        # Find all members in the test household
        household_members = self.env['dojo.member'].search([
            ('partner_id.parent_id', '=', self.household.id),
        ])

        # Should have exactly 2 members
        self.assertEqual(len(household_members), 2)

        # Should include both family members
        self.assertIn(self.member_family_1, household_members)
        self.assertIn(self.member_family_2, household_members)

    def test_module_installed(self):
        """Test that dojo_members module is installed correctly."""
        # Check that the module is installed
        module = self.env['ir.module.module'].search([('name', '=', 'dojo_members')])
        self.assertTrue(module)
        self.assertEqual(module.state, 'installed')

        # Check that menu items exist
        menu = self.env['ir.ui.menu'].search([('name', '=', 'Member Reports')])
        self.assertTrue(menu)
