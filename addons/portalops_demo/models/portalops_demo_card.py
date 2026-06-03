from odoo import fields, models


class PortalOpsDemoCard(models.Model):
    _name = "portalops.demo.card"
    _description = "PortalOps Demo Card"
    _order = "sequence, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    kind = fields.Selection(
        [
            ("insight", "Insight"),
            ("persona", "Persona"),
            ("workflow", "Workflow"),
            ("proof", "Proof"),
        ],
        default="insight",
        required=True,
    )
    headline = fields.Char(required=True)
    body = fields.Text(required=True)
    visibility = fields.Selection(
        [
            ("all", "All Perspectives"),
            ("customer", "Customer"),
            ("sales", "Sales"),
            ("manager", "Manager"),
        ],
        default="all",
        required=True,
    )
    location_id = fields.Many2one(
        "portalops.demo.location",
        required=True,
        ondelete="cascade",
    )
