from odoo import api, fields, models


class DojoMember(models.Model):
    _inherit = "dojo.member"

    event_registration_count = fields.Integer(
        compute="_compute_event_registration_count",
        string="Events",
    )

    def _compute_event_registration_count(self):
        partner_ids = self.mapped("partner_id").ids
        if not partner_ids:
            for rec in self:
                rec.event_registration_count = 0
            return
        groups = self.env["event.registration"]._read_group(
            domain=[("partner_id", "in", partner_ids)],
            groupby=["partner_id"],
            aggregates=["__count"],
        )
        count_map = {partner.id: count for partner, count in groups}
        for rec in self:
            rec.event_registration_count = count_map.get(rec.partner_id.id, 0)

    def action_view_event_registrations(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Event Registrations",
            "res_model": "event.registration",
            "view_mode": "list,form",
            "domain": [("partner_id", "=", self.partner_id.id)],
            "context": {
                "default_partner_id": self.partner_id.id,
                "default_name": self.name,
                "default_email": self.email,
                "default_phone": self.phone,
            },
        }
