from odoo import api, fields, models


class DojoEmailHistory(models.Model):
    _name = "dojo.email.history"
    _description = "Email History"
    _order = "sent_date desc"

    subject = fields.Char(required=True, string="Subject")
    body = fields.Html(string="Body")
    sent_date = fields.Datetime(
        required=True,
        default=fields.Datetime.now,
        string="Sent Date",
    )
    sender_id = fields.Many2one(
        "res.users",
        required=True,
        default=lambda self: self.env.user,
        string="Sender",
    )
    recipient_count = fields.Integer(
        string="Recipient Count",
        help="Number of members this email was sent to.",
    )
    audience_filter = fields.Char(
        string="Audience Filter",
        help="Domain or description of the audience segment (e.g. 'Active Members', 'Black Belts').",
    )
    member_ids = fields.Many2many(
        "dojo.member",
        string="Recipients",
        help="Members who received this email.",
    )
