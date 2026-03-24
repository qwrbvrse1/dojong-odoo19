from odoo import fields, models


class DojoClassSessionCrmExtension(models.Model):
    _inherit = "dojo.class.session"

    trial_lead_ids = fields.One2many(
        "crm.lead", "trial_session_id", string="Trial Leads"
    )
