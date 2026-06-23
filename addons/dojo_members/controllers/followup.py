import logging

from odoo import http, _
from odoo.http import request
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)


class DojoFollowupController(http.Controller):

    @http.route(
        "/dojo_members/send_followup",
        type="json",
        auth="user",
        methods=["POST"],
    )
    def send_followup_email(self, member_ids, subject=None, body=None):
        """Send follow-up email to inactive students.

        Args:
            member_ids (list): List of member IDs to send email to
            subject (str): Email subject (optional, uses default if not provided)
            body (str): Email body HTML (optional, uses default template if not provided)

        Returns:
            dict: {success: bool, sent_count: int, error: str (if failed)}

        Requires:
            dojo_core.group_dojo_instructor or group_dojo_admin
        """
        # Check authorization
        if not request.env.user.has_group('dojo_core.group_dojo_instructor'):
            raise AccessError(_('You are not allowed to send follow-up emails. Instructor or Admin role required.'))

        # Validate member_ids
        if not isinstance(member_ids, list) or not all(isinstance(mid, int) for mid in member_ids):
            return {"success": False, "error": "Invalid member_ids format"}

        if not member_ids:
            return {"success": False, "error": "No recipients selected"}

        # Use defaults if not provided
        if not subject:
            subject = _("We miss you at the dojo!")

        if not body:
            body = _("""
                <p>Hi,</p>
                <p>We noticed you haven't been to the dojo recently. We'd love to see you back on the mat!</p>
                <p>If you have any questions or concerns about your membership, please don't hesitate to reach out.</p>
                <p>Hope to see you soon!</p>
            """)

        members = request.env["dojo.member"].browse(member_ids)
        mail_mail = request.env["mail.mail"]

        sent_count = 0
        for member in members:
            # Get the member's email from partner
            partner = member.partner_id
            if partner and partner.email:
                mail_values = {
                    "subject": subject,
                    "body_html": body,
                    "email_to": partner.email,
                    "author_id": request.env.user.partner_id.id,
                }
                mail = mail_mail.create(mail_values)
                mail.send()
                sent_count += 1
                _logger.info(
                    "Follow-up email sent to member %s (%s) at %s",
                    member.id,
                    member.name,
                    partner.email,
                )

        return {
            "success": True,
            "sent_count": sent_count,
        }
