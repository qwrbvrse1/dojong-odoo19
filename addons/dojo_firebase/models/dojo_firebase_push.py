# -*- coding: utf-8 -*-
import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class DojoFirebasePush(models.AbstractModel):
    """Push notification helper — queries FCM tokens and dispatches notifications.

    Also owns the class reminder cron method.
    """
    _name = 'dojo.firebase.push'
    _description = 'Dojo Firebase Push Notification Service'

    # ── Token helpers ─────────────────────────────────────────────────────

    @api.model
    def _is_push_enabled(self):
        return (
            self.env['ir.config_parameter']
            .sudo()
            .get_param('firebase.push_enabled') == 'True'
        )

    @api.model
    def _get_tokens(self, partner_ids):
        """Return active FCM token strings for the given partner IDs."""
        if not partner_ids:
            return []
        tokens = self.env['dojo.fcm.token'].sudo().search([
            ('partner_id', 'in', list(partner_ids)),
            ('active', '=', True),
        ])
        return [t.token for t in tokens if t.token]

    @api.model
    def _push_to_partners(self, partner_ids, title, body, data=None):
        """Send a push notification to all active FCM tokens for *partner_ids*.

        Automatically deactivates any UNREGISTERED tokens reported by Firebase.
        Silently no-ops when push is disabled or no tokens are found.
        """
        if not self._is_push_enabled():
            return
        tokens = self._get_tokens(partner_ids)
        if not tokens:
            return

        try:
            result = self.env['dojo.firebase.service'].send_push(
                tokens=tokens,
                title=title,
                body=body,
                data=data,
            )
        except Exception as exc:
            _logger.warning('Firebase push failed (non-fatal): %s', exc)
            return

        # Deactivate unregistered tokens so they're not re-used
        stale = result.get('unregistered_tokens', [])
        if stale:
            self.env['dojo.fcm.token'].sudo().search(
                [('token', 'in', stale)]
            ).write({'active': False})
            _logger.info('Deactivated %d stale FCM tokens.', len(stale))

    # ── Cron: class reminder ──────────────────────────────────────────────

    @api.model
    def _cron_push_class_reminders(self):
        """Daily cron — push "class tomorrow" reminders to enrolled members.

        Runs once per day (configured in ir_cron_firebase.xml).
        Finds all sessions starting tomorrow, collects enrolled members'
        partners, and sends a push notification for each unique session.
        """
        if not self._is_push_enabled():
            return

        Session = self.env.get('dojo.class.session')
        Enrollment = self.env.get('dojo.class.enrollment')
        if not Session or not Enrollment:
            _logger.warning('dojo_firebase cron: dojo.class.session model not available — skipping.')
            return

        tomorrow_start = fields.Datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)
        tomorrow_end = tomorrow_start + timedelta(days=1)

        sessions = Session.sudo().search([
            ('start_datetime', '>=', tomorrow_start),
            ('start_datetime', '<', tomorrow_end),
            ('state', 'not in', ['cancelled', 'done']),
        ])

        if not sessions:
            return

        for session in sessions:
            enrollments = Enrollment.sudo().search([
                ('session_id', '=', session.id),
                ('status', '=', 'registered'),
            ])
            if not enrollments:
                continue

            partner_ids = [
                e.member_id.partner_id.id
                for e in enrollments
                if e.member_id and e.member_id.partner_id
            ]
            if not partner_ids:
                continue

            # Format time in a user-friendly way (naive local display)
            session_time = fields.Datetime.context_timestamp(
                session, session.start_datetime
            ).strftime('%I:%M %p').lstrip('0')

            self._push_to_partners(
                partner_ids=partner_ids,
                title='Class Tomorrow! 🥋',
                body=f'{session.name or "Your class"} at {session_time}',
                data={
                    'type': 'class_reminder',
                    'session_id': str(session.id),
                },
            )

        _logger.info(
            'Firebase class reminder cron: processed %d session(s) for tomorrow.',
            len(sessions),
        )
