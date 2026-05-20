"""Extends ``automation.configuration`` from automation_oca with:

- a ``trigger_template_id`` link to a Dojang pre-built trigger
- include/exclude tag filters using the inherited ``res.partner.category``
- a contact-type selector for templates that support it
- domain composition that splices these dojo filters into the base domain
"""

import json

from odoo import api, fields, models


CONTACT_TYPE_SELECTION = [
    ("any", "Any Status"),
    ("lead", "Prospect"),
    ("trial", "Assessment"),
    ("active", "Active Resident"),
    ("paused", "Paused Services"),
    ("cancelled", "Discharged"),
]


class AutomationConfiguration(models.Model):
    _inherit = "automation.configuration"

    trigger_template_id = fields.Many2one(
        "dojo.automation.trigger.template",
        string="Pre-built Trigger",
        ondelete="set null",
        help="Pick a pre-built trigger to populate model, domain, and "
        "scheduling defaults.",
    )
    trigger_template_code = fields.Char(
        related="trigger_template_id.code", store=True
    )

    tag_include_ids = fields.Many2many(
        "res.partner.category",
        relation="dojo_automation_config_tag_include_rel",
        column1="config_id",
        column2="category_id",
        string="Include Tags",
        help="Only members carrying any of these tags qualify.",
    )
    tag_exclude_ids = fields.Many2many(
        "res.partner.category",
        relation="dojo_automation_config_tag_exclude_rel",
        column1="config_id",
        column2="category_id",
        string="Exclude Tags",
        help="Members carrying any of these tags are skipped.",
    )
    contact_type = fields.Selection(
        CONTACT_TYPE_SELECTION,
        default="any",
        string="Contact Type",
    )

    # ── Domain composition ────────────────────────────────────────────────
    @api.onchange("trigger_template_id")
    def _onchange_trigger_template_id(self):
        for rec in self:
            tpl = rec.trigger_template_id
            if not tpl:
                continue
            rec.model_id = tpl.model_id
            rec.is_periodic = tpl.is_periodic_default
            if tpl.default_field_id:
                rec.field_id = tpl.default_field_id
            base = tpl.default_domain or "[]"
            # Set inline editable_domain on first selection so the user
            # can see and tweak what was applied.
            rec.editable_domain = base

    def _dojo_extra_domain(self):
        """Return a list of domain leaves derived from the dojo filter UI.

        Tag filters apply when the target model is ``dojo.member`` (which
        ``_inherits`` ``res.partner``) or directly ``res.partner``. For
        other models the tag/contact filters are silently ignored — the
        UI hides the controls in those cases.
        """
        self.ensure_one()
        leaves = []
        model = self.model_id.model or ""
        partner_path = None
        if model == "res.partner":
            partner_path = ""
        elif model == "dojo.member":
            partner_path = "partner_id."
        if partner_path is not None:
            if self.tag_include_ids:
                leaves.append(
                    (f"{partner_path}category_id", "in", self.tag_include_ids.ids)
                )
            if self.tag_exclude_ids:
                leaves.append(
                    (f"{partner_path}category_id", "not in", self.tag_exclude_ids.ids)
                )
        if model == "dojo.member" and self.contact_type and self.contact_type != "any":
            leaves.append(("membership_state", "=", self.contact_type))
        return leaves

    @api.depends(
        "filter_id",
        "filter_id.domain",
        "editable_domain",
        "tag_include_ids",
        "tag_exclude_ids",
        "contact_type",
        "model_id",
    )
    def _compute_domain(self):
        # Let the base implementation populate ``domain`` from the filter or
        # editable_domain first, then splice in the dojo extras.
        super()._compute_domain()
        for rec in self:
            extra = rec._dojo_extra_domain()
            if not extra:
                continue
            try:
                base = json.loads(rec.domain or "[]")
            except (ValueError, TypeError):
                base = []
            if not isinstance(base, list):
                base = []
            rec.domain = json.dumps(list(base) + extra)
