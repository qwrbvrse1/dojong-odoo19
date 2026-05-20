from odoo import api, fields, models


CATEGORY_SELECTION = [
    ("member", "Resident Lifecycle"),
    ("attendance", "Check-Ins"),
    ("subscription", "Billing & Coverage"),
    ("belt", "Progress Milestones"),
    ("tag", "Cohort Tags"),
    ("date", "Calendar Events"),
    ("system", "System"),
]


class DojoAutomationTriggerTemplate(models.Model):
    """Pre-built triggers presented to dojo staff in the simplified
    automation builder. Each template hydrates an ``automation.configuration``
    with sensible defaults so admins do not have to think about Odoo models
    and domains.
    """

    _name = "dojo.automation.trigger.template"
    _description = "Dojang Automation Trigger Template"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(
        required=True,
        help="Stable identifier used by XML data and code references.",
    )
    description = fields.Text(translate=True)
    icon = fields.Char(
        default="fa-bolt",
        help="Font Awesome icon class shown in the trigger picker.",
    )
    category = fields.Selection(
        CATEGORY_SELECTION,
        required=True,
        default="member",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    model_id = fields.Many2one(
        "ir.model",
        string="Target Model",
        required=True,
        ondelete="cascade",
    )
    model = fields.Char(related="model_id.model", store=True)

    default_domain = fields.Char(
        string="Default Domain",
        default="[]",
        help="Odoo domain pre-applied when this template is selected.",
    )
    default_field_id = fields.Many2one(
        "ir.model.fields",
        string="Deduplicate By Field",
        domain="[('model_id', '=', model_id)]",
        help="Optional unicity field on the target model.",
    )
    is_periodic_default = fields.Boolean(default=True)
    supports_tag_filter = fields.Boolean(
        default=False,
        help="Show the include/exclude tag picker when this trigger is selected.",
    )
    supports_contact_type = fields.Boolean(
        default=False,
        help="Show the contact-type selector when this trigger is selected.",
    )

    _sql_constraints = [
        ("code_uniq", "unique(code)", "Trigger template code must be unique."),
    ]

    def get_picker_payload(self):
        """Return a JSON-serialisable dict the OWL trigger picker consumes."""
        self.ensure_one()
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "description": self.description or "",
            "icon": self.icon or "fa-bolt",
            "category": self.category,
            "model_id": self.model_id.id,
            "model": self.model,
            "default_domain": self.default_domain or "[]",
            "default_field_id": self.default_field_id.id or False,
            "is_periodic_default": self.is_periodic_default,
            "supports_tag_filter": self.supports_tag_filter,
            "supports_contact_type": self.supports_contact_type,
        }
