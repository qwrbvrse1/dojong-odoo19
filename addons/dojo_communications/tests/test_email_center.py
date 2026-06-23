from odoo.tests import TransactionCase


class TestEmailCenter(TransactionCase):
    """Tests for Email Center functionality."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.belt_rank_white = cls.env["dojo.belt.rank"].create({
            "name": "White Belt",
            "sequence": 10,
            "color": "#ffffff",
        })

        cls.belt_rank_black = cls.env["dojo.belt.rank"].create({
            "name": "Black Belt",
            "sequence": 100,
            "color": "#000000",
        })

        cls.class_group_kids = cls.env["dojo.class.group"].create({
            "name": "Kids Class",
        })

        cls.class_group_adults = cls.env["dojo.class.group"].create({
            "name": "Adults Class",
        })

        cls.member_active_white = cls.env["dojo.member"].create({
            "name": "Alice White",
            "email": "alice@example.com",
            "membership_state": "active",
        })
        cls.env["dojo.member.rank"].create({
            "member_id": cls.member_active_white.id,
            "rank_id": cls.belt_rank_white.id,
        })
        cls.member_active_white.class_group_ids = [(6, 0, [cls.class_group_kids.id])]

        cls.member_trial_black = cls.env["dojo.member"].create({
            "name": "Bob Black",
            "email": "bob@example.com",
            "membership_state": "trial",
        })
        cls.env["dojo.member.rank"].create({
            "member_id": cls.member_trial_black.id,
            "rank_id": cls.belt_rank_black.id,
        })
        cls.member_trial_black.class_group_ids = [(6, 0, [cls.class_group_adults.id])]

        cls.member_paused = cls.env["dojo.member"].create({
            "name": "Charlie Paused",
            "email": "charlie@example.com",
            "membership_state": "paused",
        })

    def test_email_history_creation(self):
        """Email history record is created with correct recipient count."""
        history = self.env["dojo.email.history"].create({
            "subject": "Test Email",
            "body": "<p>This is a test email.</p>",
            "recipient_count": 2,
            "audience_filter": "Active Members",
            "member_ids": [(6, 0, [self.member_active_white.id, self.member_trial_black.id])],
        })

        self.assertEqual(history.subject, "Test Email")
        self.assertEqual(history.recipient_count, 2)
        self.assertIn(self.member_active_white, history.member_ids)
        self.assertIn(self.member_trial_black, history.member_ids)

    def test_send_email_via_model(self):
        """Email send creates mail records and history entry."""
        from unittest.mock import patch

        # Mock the mail.send() to avoid actual email sending in test
        with patch.object(type(self.env['mail.mail']), 'send'):
            member_ids = [self.member_active_white.id, self.member_trial_black.id]
            members = self.env["dojo.member"].browse(member_ids)

            sent_count = 0
            for member in members:
                partner = member._mail_get_partners().get(member.id, member.partner_id)
                if partner and partner.email:
                    mail_values = {
                        "subject": "Test Subject",
                        "body_html": "<p>Test body</p>",
                        "email_to": partner.email,
                        "author_id": self.env.user.partner_id.id,
                    }
                    mail = self.env["mail.mail"].create(mail_values)
                    mail.send()
                    sent_count += 1

            history = self.env["dojo.email.history"].create({
                "subject": "Test Subject",
                "body": "<p>Test body</p>",
                "recipient_count": sent_count,
                "audience_filter": "Active Members",
                "member_ids": [(6, 0, member_ids)],
            })

            self.assertEqual(sent_count, 2)
            self.assertTrue(history)
            self.assertEqual(history.recipient_count, 2)
            self.assertEqual(history.audience_filter, "Active Members")

    def test_get_members_by_membership_state(self):
        """Members filter by membership state correctly."""
        domain = [("membership_state", "in", ["active"])]
        members = self.env["dojo.member"].search(domain)

        member_ids = members.ids
        self.assertIn(self.member_active_white.id, member_ids)
        self.assertNotIn(self.member_trial_black.id, member_ids)
        self.assertNotIn(self.member_paused.id, member_ids)

    def test_get_members_by_belt_rank(self):
        """Members filter by belt rank correctly."""
        domain = [("current_rank_id", "=", self.belt_rank_black.id)]
        members = self.env["dojo.member"].search(domain)

        member_ids = members.ids
        self.assertIn(self.member_trial_black.id, member_ids)
        self.assertNotIn(self.member_active_white.id, member_ids)

    def test_get_members_by_class_group(self):
        """Members filter by class group correctly."""
        domain = [("class_group_ids", "in", [self.class_group_kids.id])]
        members = self.env["dojo.member"].search(domain)

        member_ids = members.ids
        self.assertIn(self.member_active_white.id, member_ids)
        self.assertNotIn(self.member_trial_black.id, member_ids)
