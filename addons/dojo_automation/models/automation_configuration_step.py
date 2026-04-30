"""Extends ``automation.configuration.step`` with first-class fields for the
SMS step type so the server action can read them directly without parsing
JSON (which is forbidden inside safe_eval'd ir.actions.server code).
"""

from odoo import fields, models


class AutomationConfigurationStep(models.Model):
    _inherit = "automation.configuration.step"

    sms_template_id = fields.Many2one(
        "sms.template",
        string="SMS Template",
        ondelete="set null",
        help="SMS template rendered against the step record when the SMS "
        "server action fires.",
    )
    phone_field = fields.Char(
        string="Phone Field",
        help="Optional dotted field path on the step record used to find a "
        "phone number. Falls back to mobile / phone / partner_id.mobile.",
    )
