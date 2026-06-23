# -*- coding: utf-8 -*-
"""Tests for membership expiry warning email automation."""

from datetime import timedelta
from odoo import fields
from odoo.tests.common import TransactionCase


class TestExpiryAutomation(TransactionCase):
    """Test the membership expiry warning email automation cron job."""

    def setUp(self):
        super().setUp()
        self.Member = self.env['dojo.member']
        self.Template = self.env['mail.template']
        self.ConfigParam = self.env['ir.config_parameter']

        # Create test members with different expiry dates
        today = fields.Date.today()
        self.member_expiring_today = self.Member.create({
            'name': 'Expiring Today',
            'email': 'today@test.com',
            'expdate': today,
        })
        self.member_expiring_in_7_days = self.Member.create({
            'name': 'Expiring in 7 Days',
            'email': 'in7days@test.com',
            'expdate': today + timedelta(days=7),
        })
        self.member_expiring_in_30_days = self.Member.create({
            'name': 'Expiring in 30 Days',
            'email': 'in30days@test.com',
            'expdate': today + timedelta(days=30),
        })
        self.member_expiring_in_60_days = self.Member.create({
            'name': 'Expiring in 60 Days',
            'email': 'in60days@test.com',
            'expdate': today + timedelta(days=60),
        })
        self.member_no_expdate = self.Member.create({
            'name': 'No Expiry Date',
            'email': 'noexpdate@test.com',
        })
        self.member_no_email = self.Member.create({
            'name': 'No Email',
            'expdate': today + timedelta(days=15),
        })
        self.member_expired_yesterday = self.Member.create({
            'name': 'Expired Yesterday',
            'email': 'expired@test.com',
            'expdate': today - timedelta(days=1),
        })

        # Reset mail.mail to track sent emails
        self.env['mail.mail'].search([]).unlink()

    def test_expiry_warning_default_30_days(self):
        """Test that cron sends emails to members expiring within 30 days when days_ahead=30."""
        self.ConfigParam.sudo().set_param('dojo_automation.expiry_days_ahead', '30')

        # Run the cron
        self.Member._cron_send_expiry_warning_emails()

        # Check that three emails were queued (today, 7 days, 30 days)
        mails = self.env['mail.mail'].search([])
        self.assertEqual(len(mails), 3, "Expected exactly 3 expiry warning emails to be queued")
        emails = [mail.email_to for mail in mails]
        self.assertIn('today@test.com', str(emails))
        self.assertIn('in7days@test.com', str(emails))
        self.assertIn('in30days@test.com', str(emails))

    def test_expiry_warning_7_days_ahead(self):
        """Test that cron respects the days_ahead configuration."""
        self.ConfigParam.sudo().set_param('dojo_automation.expiry_days_ahead', '7')

        # Run the cron
        self.Member._cron_send_expiry_warning_emails()

        # Check that two emails were queued (today + 7 days)
        mails = self.env['mail.mail'].search([])
        self.assertEqual(len(mails), 2, "Expected 2 expiry warning emails when days_ahead=7")
        emails = [mail.email_to for mail in mails]
        self.assertIn('today@test.com', str(emails))
        self.assertIn('in7days@test.com', str(emails))
        self.assertNotIn('in30days@test.com', str(emails))

    def test_expiry_warning_excludes_no_email(self):
        """Test that members without email are excluded."""
        self.ConfigParam.sudo().set_param('dojo_automation.expiry_days_ahead', '30')

        # Run the cron
        self.Member._cron_send_expiry_warning_emails()

        # Check that member_no_email did not receive an email
        mails = self.env['mail.mail'].search([])
        self.assertTrue(
            all('No Email' not in mail.body_html for mail in mails),
            "Member without email should not receive expiry warning email"
        )

    def test_expiry_warning_excludes_no_expdate(self):
        """Test that members without an expiry date are excluded."""
        self.ConfigParam.sudo().set_param('dojo_automation.expiry_days_ahead', '30')

        # Run the cron
        self.Member._cron_send_expiry_warning_emails()

        # Check that member_no_expdate did not receive an email
        mails = self.env['mail.mail'].search([])
        self.assertTrue(
            all('noexpdate@test.com' not in mail.email_to for mail in mails),
            "Member without expiry date should not receive email"
        )

    def test_expiry_warning_excludes_already_expired(self):
        """Test that members whose membership already expired are excluded."""
        self.ConfigParam.sudo().set_param('dojo_automation.expiry_days_ahead', '30')

        # Run the cron
        self.Member._cron_send_expiry_warning_emails()

        # Check that member_expired_yesterday did not receive an email
        mails = self.env['mail.mail'].search([])
        self.assertTrue(
            all('expired@test.com' not in mail.email_to for mail in mails),
            "Member whose membership already expired should not receive warning email"
        )

    def test_expiry_warning_excludes_far_future(self):
        """Test that members expiring beyond the threshold are excluded."""
        self.ConfigParam.sudo().set_param('dojo_automation.expiry_days_ahead', '30')

        # Run the cron
        self.Member._cron_send_expiry_warning_emails()

        # Check that member_expiring_in_60_days did not receive an email
        mails = self.env['mail.mail'].search([])
        self.assertTrue(
            all('in60days@test.com' not in mail.email_to for mail in mails),
            "Member expiring beyond threshold should not receive warning email"
        )

    def test_expiry_email_template_exists(self):
        """Test that the expiry warning email template is installed."""
        template = self.env.ref('dojo_automation.email_tpl_expiry_warning', raise_if_not_found=False)
        self.assertTrue(template, "Expiry warning email template should exist")
        self.assertEqual(template.model_id.model, 'dojo.member', "Template should target dojo.member")

    def test_expiry_cron_record_exists(self):
        """Test that the expiry warning cron record is installed."""
        cron = self.env.ref('dojo_automation.ir_cron_expiry_warning_emails', raise_if_not_found=False)
        self.assertTrue(cron, "Expiry warning cron should exist")
        self.assertTrue(cron.active, "Expiry warning cron should be active by default")
        self.assertEqual(cron.interval_type, 'days', "Cron should run daily")
        self.assertEqual(cron.interval_number, 1, "Cron should run every 1 day")

    def test_config_parameter_exists(self):
        """Test that the configuration parameter exists with correct default."""
        param = self.ConfigParam.sudo().get_param('dojo_automation.expiry_days_ahead', None)
        self.assertIsNotNone(param, "Configuration parameter should exist")
        self.assertEqual(param, '30', "Default days_ahead should be 30")
