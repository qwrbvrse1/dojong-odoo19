import logging
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install", "dojo_members")
class TestFollowupEmail(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create test members with email
        cls.member1 = cls.env['dojo.member'].create({
            'name': 'Test Member One',
            'email': 'member1@example.com',
            'membership_state': 'active',
        })

        cls.member2 = cls.env['dojo.member'].create({
            'name': 'Test Member Two',
            'email': 'member2@example.com',
            'membership_state': 'active',
        })

        cls.member_no_email = cls.env['dojo.member'].create({
            'name': 'Member No Email',
            'membership_state': 'active',
        })

    def test_followup_controller_exists(self):
        """Test that the followup controller module can be imported."""
        from odoo.addons.dojo_members.controllers import followup
        self.assertTrue(hasattr(followup, 'DojoFollowupController'))

    def test_members_have_email_field(self):
        """Test that members can have email addresses."""
        self.assertEqual(self.member1.email, 'member1@example.com')
        self.assertEqual(self.member2.email, 'member2@example.com')
        self.assertFalse(self.member_no_email.email)

    def test_member_partner_exists(self):
        """Test that members have associated partners."""
        self.assertTrue(self.member1.partner_id)
        self.assertEqual(self.member1.partner_id.email, 'member1@example.com')

    def test_mail_mail_model_exists(self):
        """Test that mail.mail model is available for sending emails."""
        # Check that the model exists and can be accessed
        self.assertIn('mail.mail', self.env)
        mail_model = self.env['mail.mail']
        # Verify we can search (empty search is fine)
        mail_model.search([])

    def test_followup_route_registered(self):
        """Test that the follow-up controller method exists."""
        from odoo.addons.dojo_members.controllers.followup import DojoFollowupController
        controller = DojoFollowupController()
        self.assertTrue(hasattr(controller, 'send_followup_email'))
        # Verify the method is callable
        self.assertTrue(callable(controller.send_followup_email))
