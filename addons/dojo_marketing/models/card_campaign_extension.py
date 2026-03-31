from odoo import api, models


class CardCampaignDojo(models.Model):
    _inherit = "card.campaign"

    @api.model
    def _get_model_selection(self):
        selection = super()._get_model_selection()
        if ("dojo.member", "Dojo Member") not in selection:
            selection.append(("dojo.member", "Dojo Member"))
        return selection
