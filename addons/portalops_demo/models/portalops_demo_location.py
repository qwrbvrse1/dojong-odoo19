from odoo import fields, models


class PortalOpsDemoLocation(models.Model):
    _name = "portalops.demo.location"
    _description = "PortalOps Demo Location"
    _order = "name"

    name = fields.Char(required=True)
    slug = fields.Char(required=True, index=True)
    is_published = fields.Boolean(default=True)
    headline = fields.Char()
    summary = fields.Text()
    address_line = fields.Char()
    city = fields.Char()
    state_code = fields.Char()
    postal_code = fields.Char()
    country_code = fields.Char(default="US")
    google_place_id = fields.Char(index=True)
    google_maps_place_url = fields.Char()
    latitude = fields.Float(digits=(16, 8))
    longitude = fields.Float(digits=(16, 8))
    plus_code = fields.Char()
    grounding_status = fields.Selection(
        [
            ("not_configured", "Not Configured"),
            ("pending", "Pending"),
            ("resolved", "Resolved"),
            ("failed", "Failed"),
        ],
        default="not_configured",
        required=True,
    )
    grounding_last_error = fields.Text()
    grounding_last_resolved_at = fields.Datetime()
    card_ids = fields.One2many(
        "portalops.demo.card",
        "location_id",
        string="Cards",
    )
    audit_event_ids = fields.One2many(
        "portalops.demo.audit_event",
        "location_id",
        string="Audit Events",
    )
