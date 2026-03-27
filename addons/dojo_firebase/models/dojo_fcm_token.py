# -*- coding: utf-8 -*-
from odoo import api, fields, models


class DojoFcmToken(models.Model):
    """FCM registration token per partner device.

    When a member logs into the portal and grants notification permission, the
    Firebase JS SDK generates a registration token that is stored here via the
    /dojo/firebase/register-token endpoint.  Tokens are deactivated automatically
    when Firebase reports them as UNREGISTERED.
    """
    _name = 'dojo.fcm.token'
    _description = 'FCM Push Notification Token'
    _order = 'last_seen desc'

    partner_id = fields.Many2one(
        'res.partner',
        required=True,
        index=True,
        ondelete='cascade',
        string='Partner',
    )
    token = fields.Char(required=True, index=True, string='FCM Token')
    device_type = fields.Selection(
        [('pwa', 'Browser / PWA')],
        default='pwa',
        required=True,
        string='Device Type',
    )
    active = fields.Boolean(default=True)
    last_seen = fields.Datetime(
        default=fields.Datetime.now,
        string='Last Registered',
        help='Updated each time the client refreshes its FCM token.',
    )

    _sql_constraints = [
        ('token_uniq', 'unique(token)', 'Each FCM registration token must be unique.'),
    ]

    @api.model
    def register_or_refresh(self, partner_id, token, device_type='pwa'):
        """Upsert an FCM token for the given partner.

        If the token already exists (even if deactivated) it is reactivated and
        its last_seen timestamp is updated.  An old token belonging to the same
        partner on the same device type is replaced if it differs from *token*.
        """
        existing = self.search([('token', '=', token)], limit=1)
        if existing:
            existing.write({'active': True, 'last_seen': fields.Datetime.now(), 'partner_id': partner_id})
            return existing

        # Deactivate any stale tokens for this partner+device combination that
        # haven't been seen in the last 90 days (they're likely rotated out).
        self.search([
            ('partner_id', '=', partner_id),
            ('device_type', '=', device_type),
            ('token', '!=', token),
        ]).write({'active': False})

        return self.create({
            'partner_id': partner_id,
            'token': token,
            'device_type': device_type,
        })
