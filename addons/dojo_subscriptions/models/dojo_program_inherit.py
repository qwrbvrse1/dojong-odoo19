from odoo import api, fields, models


class DojoProgramSubscriptionExt(models.Model):
    """Add subscription plan relationship to dojo.program (defined here to avoid
    circular imports — dojo_subscriptions depends on dojo_classes, not the other way)."""

    _inherit = "dojo.program"

    plan_ids = fields.Many2many(
        "dojo.subscription.plan",
        "dojo_sub_plan_program_rel",
        "program_id",
        "plan_id",
        string="Subscription Plans",
    )
    plan_count = fields.Integer(compute="_compute_plan_count", store=True)

    @api.depends("plan_ids")
    def _compute_plan_count(self):
        for rec in self:
            rec.plan_count = len(rec.plan_ids)

    def action_view_plans(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Subscription Plans",
            "res_model": "dojo.subscription.plan",
            "view_mode": "list,form",
            "domain": [("program_ids", "in", [self.id])],
            "context": {
                "default_program_ids": [(4, self.id)],
                "default_plan_type": "program",
            },
        }
