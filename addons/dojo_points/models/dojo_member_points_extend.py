from odoo import api, fields, models

# Tier thresholds — evaluated top-down (first match wins)
_TIERS = [
    (3000, "Dojo Legend 🌟"),
    (1500, "Elite Champion 🏆"),
    (700, "Belt Breaker 💪"),
    (300, "Dedicated Martial Artist 🔥"),
    (100, "Rising Fighter ⚡"),
    (0, "Rookie Warrior 🥋"),
]


class DojoMemberPointsExtend(models.Model):
    """Adds points gamification fields to dojo.member."""

    _inherit = "dojo.member"

    # ── Ledger link ───────────────────────────────────────────────────────
    points_transaction_ids = fields.One2many(
        "dojo.points.transaction",
        "member_id",
        string="Points History",
        readonly=True,
    )

    # ── Totals + tier ─────────────────────────────────────────────────────
    total_points = fields.Integer(
        string="Total Points",
        compute="_compute_total_points",
        store=True,
    )
    points_tier = fields.Char(
        string="Points Tier",
        compute="_compute_points_tier",
        help="Motivational title based on total lifetime points.",
    )

    # ── Streak ────────────────────────────────────────────────────────────
    current_streak = fields.Integer(
        string="Current Streak",
        default=0,
        copy=False,
        help=(
            "Consecutive enrolled classes attended without an absence. "
            "Resets to 0 when any enrolled session is marked absent."
        ),
    )
    longest_streak = fields.Integer(
        string="Longest Streak",
        default=0,
        copy=False,
    )

    # ── Dedup tracking ────────────────────────────────────────────────────
    milestone_points_sent = fields.Char(
        string="Milestone Points Awarded",
        default="",
        copy=False,
        help=(
            "Comma-separated attendance milestones that have already earned points "
            "(e.g. '10,25,50'). Lifetime — does NOT reset on belt promotion."
        ),
    )

    # ── Computed ──────────────────────────────────────────────────────────

    @api.depends("points_transaction_ids.amount")
    def _compute_total_points(self):
        for member in self:
            member.total_points = sum(member.points_transaction_ids.mapped("amount"))

    @api.depends("total_points")
    def _compute_points_tier(self):
        for member in self:
            total = member.total_points or 0
            tier = "Rookie Warrior 🥋"
            for threshold, title in _TIERS:
                if total >= threshold:
                    tier = title
                    break
            member.points_tier = tier

    # ── Actions ───────────────────────────────────────────────────────────

    def action_open_points_ledger(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"{self.name} — Points History",
            "res_model": "dojo.points.transaction",
            "view_mode": "list,form",
            "domain": [("member_id", "=", self.id)],
            "context": {"default_member_id": self.id},
        }

    def action_open_award_points_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Award Points",
            "res_model": "dojo.points.award.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_member_id": self.id},
        }
