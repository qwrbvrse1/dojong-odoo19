# -*- coding: utf-8 -*-
"""Tests for birthday email automation."""

from datetime import timedelta
from odoo import fields
from odoo.tests.common import TransactionCase


class TestBirthdayAutomation(TransactionCase):
    """Test the birthday email automation cron job."""

    def setUp(self):
        super().setUp()
        self.Member = self.env['dojo.member']
        self.Template = self.env['mail.template']
        self.ConfigParam = self.env['ir.config_parameter']

        # Create test members with different birthdays
        today = fields.Date.today()
        self.member_today = self.Member.create({
            'name': 'Today Birthday',
            'date_of_birth': today.replace(year=2000),
            'email': 'today@test.com',
        })
        self.member_tomorrow = self.Member.create({
            'name': 'Tomorrow Birthday',
            'date_of_birth': (today + timedelta(days=1)).replace(year=2000),
            'email': 'tomorrow@test.com',
        })
        self.member_in_3_days = self.Member.create({
            'name': 'Birthday in 3 Days',
            'date_of_birth': (today + timedelta(days=3)).replace(year=2000),
            'email': 'in3days@test.com',
        })
        self.member_no_birthday = self.Member.create({
            'name': 'No Birthday Set',
            'email': 'nobirthday@test.com',
        })
        self.member_no_email = self.Member.create({
            'name': 'No Email',
            'date_of_birth': today.replace(year=2000),
        })

        # Reset mail.mail to track sent emails
        self.env['mail.mail'].search([]).unlink()

    def test_birthday_email_today_only(self):
        """Test that cron sends emails only to members with birthday today when days_ahead=0."""
        self.ConfigParam.sudo().set_param('dojo_automation.birthday_days_ahead', '0')

        # Run the cron
        self.Member._cron_send_birthday_emails()

        # Check that only one email was queued (to member_today)
        mails = self.env['mail.mail'].search([])
        self.assertEqual(len(mails), 1, "Expected exactly 1 birthday email to be queued")
        self.assertIn('today@test.com', mails[0].email_to, "Email should be sent to today@test.com")

    def test_birthday_email_days_ahead(self):
        """Test that cron respects the days_ahead configuration."""
        self.ConfigParam.sudo().set_param('dojo_automation.birthday_days_ahead', '1')

        # Run the cron
        self.Member._cron_send_birthday_emails()

        # Check that two emails were queued (today + tomorrow)
        mails = self.env['mail.mail'].search([])
        self.assertEqual(len(mails), 2, "Expected 2 birthday emails when days_ahead=1")
        emails = [mail.email_to for mail in mails]
        self.assertIn('today@test.com', str(emails))
        self.assertIn('tomorrow@test.com', str(emails))

    def test_birthday_email_excludes_no_email(self):
        """Test that members without email are excluded."""
        self.ConfigParam.sudo().set_param('dojo_automation.birthday_days_ahead', '0')

        # Run the cron
        self.Member._cron_send_birthday_emails()

        # Check that member_no_email did not receive an email
        mails = self.env['mail.mail'].search([])
        self.assertTrue(
            all('No Email' not in mail.body_html for mail in mails),
            "Member without email should not receive birthday email"
        )

    def test_birthday_email_excludes_no_birthday(self):
        """Test that members without a birthdate are excluded."""
        self.ConfigParam.sudo().set_param('dojo_automation.birthday_days_ahead', '10')

        # Run the cron
        self.Member._cron_send_birthday_emails()

        # Check that member_no_birthday did not receive an email
        mails = self.env['mail.mail'].search([])
        self.assertTrue(
            all('nobirthday@test.com' not in mail.email_to for mail in mails),
            "Member without birthday should not receive email"
        )

    def test_birthday_email_template_exists(self):
        """Test that the birthday email template is installed."""
        template = self.env.ref('dojo_automation.email_tpl_birthday', raise_if_not_found=False)
        self.assertTrue(template, "Birthday email template should exist")
        self.assertEqual(template.model_id.model, 'dojo.member', "Template should target dojo.member")

    def test_birthday_cron_record_exists(self):
        """Test that the birthday cron record is installed."""
        cron = self.env.ref('dojo_automation.ir_cron_birthday_emails', raise_if_not_found=False)
        self.assertTrue(cron, "Birthday cron should exist")
        self.assertTrue(cron.active, "Birthday cron should be active by default")
        self.assertEqual(cron.interval_type, 'days', "Cron should run daily")
        self.assertEqual(cron.interval_number, 1, "Cron should run every 1 day")

    def test_config_parameter_exists(self):
        """Test that the configuration parameter exists with correct default."""
        param = self.ConfigParam.sudo().get_param('dojo_automation.birthday_days_ahead', None)
        self.assertIsNotNone(param, "Configuration parameter should exist")
        self.assertEqual(param, '0', "Default days_ahead should be 0")
