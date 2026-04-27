# -*- coding: utf-8 -*-
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class MailMail(models.Model):
    """Override mail.mail.send() to relay outgoing email through Firebase Cloud Functions.

    When firebase.email_enabled is True, every outgoing mail.mail record is
    dispatched via the /sendEmail Cloud Function endpoint instead of Odoo's SMTP
    server.  Set firebase.email_enabled = False (or leave the CF URL unconfigured)
    to fall back to normal Odoo SMTP behaviour at any time.
    """
    _inherit = 'mail.mail'

    def send(self, auto_commit=False, raise_exception=False, post_send_callback=None):
        icp = self.env['ir.config_parameter'].sudo()
        if not icp.get_bool('firebase.email_enabled'):
            return super().send(
                auto_commit=auto_commit,
                raise_exception=raise_exception,
                post_send_callback=post_send_callback,
            )

        # Firebase relay path — process each queued mail individually
        service = self.env['dojo.firebase.service']
        from_name = self.env.company.name or 'Dojang'

        for mail in self.filtered(lambda m: m.state in ('outgoing', 'exception')):
            recipients = self._collect_recipients(mail)
            if not recipients:
                _logger.warning('Firebase email relay: mail %s has no recipients, skipping.', mail.id)
                mail.write({'state': 'cancel'})
                if auto_commit:
                    self.env.cr.commit()
                continue

            try:
                service.send_email(
                    to_list=recipients,
                    subject=mail.subject or '',
                    html_body=mail.body_html or mail.body_arch or '',
                    from_name=from_name,
                )
                mail.write({'state': 'sent', 'failure_reason': False})
            except Exception as exc:
                _logger.error(
                    'Firebase email relay: failed to send mail %s to %s: %s',
                    mail.id, recipients, exc,
                )
                mail.write({'state': 'exception', 'failure_reason': str(exc)[:500]})
                if raise_exception:
                    raise

            if auto_commit:
                self.env.cr.commit()

        return True

    @staticmethod
    def _collect_recipients(mail):
        """Return a deduplicated list of recipient email addresses for *mail*."""
        addrs = set()

        # Explicit email_to (comma-separated, potentially "Name <addr>" format)
        if mail.email_to:
            for part in mail.email_to.split(','):
                addr = part.strip()
                # Extract bare address from "Name <addr>"
                if '<' in addr and '>' in addr:
                    addr = addr.split('<', 1)[1].split('>', 1)[0].strip()
                if addr:
                    addrs.add(addr)

        # Many2many partner recipients
        for partner in mail.recipient_ids:
            if partner.email:
                addrs.add(partner.email.strip())

        return list(addrs)
