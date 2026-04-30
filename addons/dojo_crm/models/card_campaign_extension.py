"""Add crm.lead as a valid target for the standard Odoo Marketing Card module."""
from odoo import api, models


class CardCampaignCrmLead(models.Model):
    _inherit = "card.campaign"

    @api.model
    def _get_model_selection(self):
        selection = super()._get_model_selection()
        if ("crm.lead", "CRM Lead") not in selection:
            selection.append(("crm.lead", "CRM Lead"))
        return selection
