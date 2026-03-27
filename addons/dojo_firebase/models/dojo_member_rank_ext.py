# -*- coding: utf-8 -*-
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class DojoMemberRank(models.Model):
    """Send FCM push notification when a belt promotion is recorded."""
    _inherit = 'dojo.member.rank'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        push = self.env['dojo.firebase.push']
        for rank in records:
            try:
                partner = rank.member_id.partner_id if rank.member_id else None
                if not partner:
                    continue
                rank_name = rank.rank_id.name if rank.rank_id else 'a new rank'
                push._push_to_partners(
                    partner_ids=[partner.id],
                    title='Congratulations! Belt Promotion 🏅',
                    body=f'You have been promoted to {rank_name}. Keep up the great work!',
                    data={
                        'type': 'belt_promotion',
                        'member_id': str(rank.member_id.id),
                        'rank_id': str(rank.rank_id.id) if rank.rank_id else '',
                    },
                )
            except Exception as exc:
                _logger.warning('Firebase belt promo push failed for member %s: %s', rank.member_id.id, exc)
        return records
