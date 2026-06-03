from odoo import fields, models


class PortalOpsDemoAuditEvent(models.Model):
    _name = "portalops.demo.audit_event"
    _description = "PortalOps Demo Audit Event"
    _order = "sequence, id"

    title = fields.Char(required=True)
    detail = fields.Text()
    sequence = fields.Integer(default=10)
    event_type = fields.Selection(
        [
            ("seed", "Seed"),
            ("maps", "Maps"),
            ("voice", "Voice"),
            ("crm", "CRM"),
            ("review", "Review"),
            ("browser", "Browser"),
        ],
        default="seed",
        required=True,
    )
    location_id = fields.Many2one(
        "portalops.demo.location",
        required=True,
        ondelete="cascade",
    )
