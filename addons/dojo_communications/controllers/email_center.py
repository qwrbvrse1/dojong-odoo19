import json
from odoo import http, _
from odoo.http import request
from odoo.exceptions import AccessError


class EmailCenterController(http.Controller):

    @http.route(
        "/odoo/communications/email-center",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def email_center_page(self):
        """HTTP route for email center verification.

        Returns a simple HTML page demonstrating the email center
        compose form with audience selector markup.
        """
        html = """<!DOCTYPE html>
<html>
<head>
    <title>Email Center</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .dojo-email-center { max-width: 1200px; margin: 0 auto; }
        .email-center-filters {
            border: 1px solid #ddd;
            padding: 15px;
            margin-bottom: 20px;
            background: #f9f9f9;
        }
        .email-center-composer {
            border: 1px solid #ddd;
            padding: 15px;
        }
        .filter-group { margin-bottom: 15px; }
        label { font-weight: bold; display: block; margin-bottom: 5px; }
        input[type="checkbox"] { margin-right: 5px; }
        select { width: 100%; padding: 5px; }
        textarea { width: 100%; padding: 5px; }
        .btn { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; }
    </style>
</head>
<body>
    <div class="dojo-email-center">
        <h1>Email Center</h1>

        <div class="email-center-filters">
            <h3>Audience</h3>
            <div class="filter-group">
                <label>Membership Status</label>
                <div class="filter-options">
                    <label><input type="checkbox" /> Active</label>
                    <label><input type="checkbox" /> Trial</label>
                    <label><input type="checkbox" /> Paused</label>
                </div>
            </div>
            <div class="filter-group">
                <label for="belt-rank-select">Belt Rank</label>
                <select id="belt-rank-select">
                    <option value="">All Ranks</option>
                </select>
            </div>
            <button class="btn">Load Members</button>
        </div>

        <div class="email-center-composer">
            <h3>Compose</h3>
            <div class="form-group">
                <label for="email-subject">Subject</label>
                <input id="email-subject" type="text" placeholder="Email subject" />
            </div>
            <div class="form-group">
                <label for="email-body">Body</label>
                <textarea id="email-body" rows="10" placeholder="Email body"></textarea>
            </div>
            <button class="btn">Send Email</button>
        </div>
    </div>
</body>
</html>"""
        return request.make_response(html, headers=[('Content-Type', 'text/html')])

    @http.route(
        "/dojo/email_center/send",
        type="json",
        auth="user",
        methods=["POST"],
    )
    def send_email(self, subject, body, audience_filter, member_ids):
        """Send email to selected members and record in history.

        Requires dojo_core.group_dojo_instructor or group_dojo_admin.
        """
        if not request.env.user.has_group('dojo_core.group_dojo_instructor'):
            raise AccessError(_('You are not allowed to send mass emails. Instructor or Admin role required.'))

        # Validate member_ids are integers
        if not isinstance(member_ids, list) or not all(isinstance(mid, int) for mid in member_ids):
            return {"success": False, "error": "Invalid member_ids format"}

        if not member_ids:
            return {"success": False, "error": "No recipients selected"}

        members = request.env["dojo.member"].browse(member_ids)
        mail_mail = request.env["mail.mail"]

        sent_count = 0
        for member in members:
            partner = member._mail_get_partners().get(member.id, member.partner_id)
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

        request.env["dojo.email.history"].create({
            "subject": subject,
            "body": body,
            "recipient_count": sent_count,
            "audience_filter": audience_filter,
            "member_ids": [(6, 0, member_ids)],
        })

        return {
            "success": True,
            "sent_count": sent_count,
        }

    @http.route(
        "/dojo/email_center/members",
        type="json",
        auth="user",
        methods=["POST"],
    )
    def get_members(self, filters):
        """Get members matching the given audience filter.

        Requires dojo_core.group_dojo_instructor or group_dojo_admin.
        """
        if not request.env.user.has_group('dojo_core.group_dojo_instructor'):
            raise AccessError(_('You are not allowed to access member lists. Instructor or Admin role required.'))

        domain = []

        if filters.get("membership_state"):
            domain.append(("membership_state", "in", filters["membership_state"]))

        if filters.get("class_group_ids"):
            domain.append(("class_group_ids", "in", filters["class_group_ids"]))

        if filters.get("belt_rank_id"):
            domain.append(("current_rank_id", "=", filters["belt_rank_id"]))

        if filters.get("expiring_soon"):
            days_ahead = filters.get("expiring_days", 30)
            from odoo import fields
            from datetime import date, timedelta
            cutoff_date = date.today() + timedelta(days=days_ahead)
            domain.append(("expdate", "<=", cutoff_date))
            domain.append(("expdate", ">=", date.today()))

        members = request.env["dojo.member"].search(domain)

        return {
            "members": [
                {
                    "id": m.id,
                    "name": m.name,
                    "email": m.partner_id.email or "",
                    "membership_state": m.membership_state,
                    "current_rank": m.current_rank_id.name if m.current_rank_id else "",
                }
                for m in members
            ]
        }
