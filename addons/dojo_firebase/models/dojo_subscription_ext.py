# -*- coding: utf-8 -*-
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class DojoMemberSubscription(models.Model):
    """Send FCM push notification after billing Failure #1 (dunning escalation)."""
    _inherit = 'sale.subscription'

    def _handle_billing_failure(self, exc):
        super()._handle_billing_failure(exc)
        # billing_failure_count is incremented inside super(); check after the call
        if self.billing_failure_count != 1:
            return
        try:
            partner = self._billing_partner()
            if not partner:
                return
            self.env['dojo.firebase.push']._push_to_partners(
                partner_ids=[partner.id],
                title='Payment Issue ⚠️',
                body='There was a problem processing your membership payment. '
                     'Please update your payment method in the portal.',
                data={
                    'type': 'payment_failed',
                    'subscription_id': str(self.id),
                },
            )
        except Exception as push_exc:
            _logger.warning(
                'Firebase payment-failed push failed for subscription %s: %s',
                self.id, push_exc,
            )
