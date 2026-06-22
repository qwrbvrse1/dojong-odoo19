"""Tests for dojo.member.expdate stored computed field."""
import logging
from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)


class TestMemberExpdate(TransactionCase):
    """Test suite for dojo.member.expdate field."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Member = cls.env['dojo.member']

        # Only run tests if sale.subscription is available
        if 'sale.subscription' not in cls.env:
            _logger.warning(
                'sale.subscription model not available; skipping test_member_expdate tests'
            )
            return

        cls.Subscription = cls.env['sale.subscription']
        cls.SubscriptionStage = cls.env['sale.subscription.stage']
        cls.SubscriptionTemplate = cls.env['sale.subscription.template']

        # Create stages
        cls.draft_stage = cls.SubscriptionStage.search([('type', '=', 'draft')], limit=1)
        if not cls.draft_stage:
            cls.draft_stage = cls.SubscriptionStage.create({
                'name': 'Draft',
                'type': 'draft',
            })

        cls.active_stage = cls.SubscriptionStage.search([('type', '=', 'in_progress')], limit=1)
        if not cls.active_stage:
            cls.active_stage = cls.SubscriptionStage.create({
                'name': 'Active',
                'type': 'in_progress',
            })

        cls.post_stage = cls.SubscriptionStage.search([('type', '=', 'post')], limit=1)
        if not cls.post_stage:
            cls.post_stage = cls.SubscriptionStage.create({
                'name': 'Closed',
                'type': 'post',
            })

        # Create subscription template (required by sale.subscription)
        cls.template = cls.SubscriptionTemplate.create({
            'name': 'Test Subscription Template',
            'code': 'TEST',
        })

        # Get or create a pricelist (required by sale.subscription)
        cls.pricelist = cls.env['product.pricelist'].search([], limit=1)
        if not cls.pricelist:
            cls.pricelist = cls.env['product.pricelist'].create({
                'name': 'Test Pricelist',
            })

        # Create test member
        cls.member = cls.Member.create({
            'name': 'Test Member',
            'email': 'test@example.com',
        })

    def test_expdate_no_subscription(self):
        """Test that expdate is False when member has no subscription."""
        if 'sale.subscription' not in self.env:
            self.skipTest('sale.subscription not available')

        # Member with no subscription should have False expdate
        self.assertFalse(
            self.member.expdate,
            'Member with no subscription should have False expdate'
        )

    def test_expdate_active_subscription(self):
        """Test that expdate is set from active subscription end date."""
        if 'sale.subscription' not in self.env:
            self.skipTest('sale.subscription not available')

        today = fields.Date.today()
        end_date = today + timedelta(days=30)

        # Create active subscription
        subscription = self.Subscription.create({
            'partner_id': self.member.partner_id.id,
            'member_id': self.member.id,
            'template_id': self.template.id,
            'pricelist_id': self.pricelist.id,
            'stage_id': self.active_stage.id,
            'date': end_date,
        })

        # Force recompute
        self.member._compute_expdate()

        self.assertEqual(
            self.member.expdate,
            end_date,
            'Member expdate should match active subscription end date'
        )

    def test_expdate_multiple_active_subscriptions(self):
        """Test that expdate uses latest end date when multiple active subscriptions exist."""
        if 'sale.subscription' not in self.env:
            self.skipTest('sale.subscription not available')

        today = fields.Date.today()
        end_date_1 = today + timedelta(days=30)
        end_date_2 = today + timedelta(days=60)

        # Create two active subscriptions with different end dates
        sub1 = self.Subscription.create({
            'partner_id': self.member.partner_id.id,
            'member_id': self.member.id,
            'template_id': self.template.id,
            'stage_id': self.active_stage.id,
            'date': end_date_1,
        })

        sub2 = self.Subscription.create({
            'partner_id': self.member.partner_id.id,
            'member_id': self.member.id,
            'template_id': self.template.id,
            'stage_id': self.active_stage.id,
            'date': end_date_2,
        })

        # Force recompute
        self.member._compute_expdate()

        self.assertEqual(
            self.member.expdate,
            end_date_2,
            'Member expdate should use the latest end date from active subscriptions'
        )

    def test_expdate_cancelled_subscription_ignored(self):
        """Test that cancelled subscriptions do not affect expdate."""
        if 'sale.subscription' not in self.env:
            self.skipTest('sale.subscription not available')

        today = fields.Date.today()
        end_date = today + timedelta(days=30)

        # Create cancelled subscription
        subscription = self.Subscription.create({
            'partner_id': self.member.partner_id.id,
            'member_id': self.member.id,
            'template_id': self.template.id,
            'stage_id': self.post_stage.id,
            'date': end_date,
        })

        # Force recompute
        self.member._compute_expdate()

        self.assertFalse(
            self.member.expdate,
            'Cancelled subscription should not set expdate'
        )

    def test_expdate_field_indexed(self):
        """Test that expdate field is indexed for efficient filtering."""
        if 'sale.subscription' not in self.env:
            self.skipTest('sale.subscription not available')

        # Check field definition
        field_def = self.Member._fields.get('expdate')
        self.assertTrue(
            field_def.index,
            'expdate field should be indexed'
        )

    def test_expdate_field_stored(self):
        """Test that expdate field is stored (not computed on-the-fly)."""
        if 'sale.subscription' not in self.env:
            self.skipTest('sale.subscription not available')

        # Check field definition
        field_def = self.Member._fields.get('expdate')
        self.assertTrue(
            field_def.store,
            'expdate field should be stored'
        )

    def test_expdate_draft_subscription_ignored(self):
        """Test that draft subscriptions do not affect expdate."""
        if 'sale.subscription' not in self.env:
            self.skipTest('sale.subscription not available')

        today = fields.Date.today()
        end_date = today + timedelta(days=30)

        # Create draft subscription
        subscription = self.Subscription.create({
            'partner_id': self.member.partner_id.id,
            'member_id': self.member.id,
            'template_id': self.template.id,
            'pricelist_id': self.pricelist.id,
            'stage_id': self.draft_stage.id,
            'date': end_date,
        })

        # Force recompute
        self.member._compute_expdate()

        # Draft subscription should not set expdate
        self.assertFalse(
            self.member.expdate,
            'Draft subscription should not set expdate'
        )
