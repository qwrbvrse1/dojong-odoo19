# -*- coding: utf-8 -*-
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    """Send FCM push notification when a customer invoice is sent."""
    _inherit = 'account.move'

    def action_send_and_print(self, **kwargs):
        result = super().action_send_and_print(**kwargs)
        push = self.env['dojo.firebase.push']
        for move in self.filtered(lambda m: m.move_type in ('out_invoice', 'out_receipt')):
            try:
                partner = move.partner_id
                if not partner:
                    continue
                amount = f'{abs(move.amount_total_signed):,.2f} {move.currency_id.name or ""}'.strip()
                push._push_to_partners(
                    partner_ids=[partner.id],
                    title='New Invoice Ready 📄',
                    body=f'Invoice {move.name or ""} for {amount} is available in your portal.',
                    data={
                        'type': 'invoice',
                        'move_id': str(move.id),
                    },
                )
            except Exception as exc:
                _logger.warning('Firebase invoice push failed for move %s: %s', move.id, exc)
        return result
