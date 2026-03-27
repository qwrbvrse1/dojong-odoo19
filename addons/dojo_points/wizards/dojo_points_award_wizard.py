from odoo import api, fields, models
from odoo.exceptions import UserError


class DojoPointsAwardWizard(models.TransientModel):
    """Wizard for instructors to manually award points to a member."""

    _name = "dojo.points.award.wizard"
    _description = "Award Points to Member"

    member_id = fields.Many2one(
        "dojo.member",
        string="Member",
        required=True,
        default=lambda self: self.env.context.get("default_member_id"),
    )
    amount = fields.Integer(
        string="Points to Award",
        required=True,
        default=10,
        help="Must be greater than 0.",
    )
    note = fields.Char(
        string="Reason",
        required=True,
        help="Briefly describe why these points are being awarded.",
    )

    @api.constrains("amount")
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise UserError("Points awarded must be a positive number.")

    def action_award(self):
        self.ensure_one()
        config = self.env["dojo.points.config"].sudo().get_singleton()

        if not config.instructor_award_enabled:
            raise UserError(
                "Instructor point awards are currently disabled. "
                "Contact an administrator to enable them."
            )

        # Daily cap check
        cap = config.max_instructor_award_per_day
        if cap > 0:
            today_start = fields.Datetime.today()
            today_txns = self.env["dojo.points.transaction"].sudo().search([
                ("member_id", "=", self.member_id.id),
                ("source_type", "=", "instructor_award"),
                ("date", ">=", today_start),
            ])
            awarded_today = sum(today_txns.mapped("amount"))
            if awarded_today + self.amount > cap:
                remaining = max(cap - awarded_today, 0)
                raise UserError(
                    f"This award would exceed the daily instructor cap of {cap} pts "
                    f"for {self.member_id.name}. "
                    f"You can still award up to {remaining} pts today."
                )

        self.env["dojo.points.transaction"].sudo().create({
            "member_id": self.member_id.id,
            "source_type": "instructor_award",
            "amount": self.amount,
            "note": self.note,
            "awarded_by": self.env.user.id,
        })

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Points Awarded! 🏆",
                "message": f"Awarded {self.amount} pts to {self.member_id.name}.",
                "type": "success",
                "sticky": False,
            },
        }
