from odoo import api, fields, models


class DojoPointsConfig(models.Model):
    _name = "dojo.points.config"
    _description = "Dojang Points Configuration"
    _rec_name = "id"

    # ── Attendance ────────────────────────────────────────────────────────
    attendance_points = fields.Integer(
        string="Points per Class (Present)", default=10,
        help="Awarded each time a member checks in as Present.",
    )
    late_attendance_points = fields.Integer(
        string="Points per Class (Late)", default=5,
        help="Awarded each time a member checks in as Late.",
    )

    # ── Streak bonuses ────────────────────────────────────────────────────
    streak_bonus_3 = fields.Integer(
        string="3-Class Streak Bonus", default=15,
        help="Bonus awarded when member hits a 3-class consecutive streak.",
    )
    streak_bonus_7 = fields.Integer(
        string="7-Class Streak Bonus", default=50,
    )
    streak_bonus_30 = fields.Integer(
        string="30-Class Streak Bonus", default=200,
    )

    # ── Belt promotion ────────────────────────────────────────────────────
    belt_promotion_points = fields.Integer(
        string="Belt Promotion Points", default=100,
        help="Awarded each time a member earns a new belt rank.",
    )

    # ── Attendance milestones ─────────────────────────────────────────────
    milestone_10_points = fields.Integer(string="10-Class Milestone", default=50)
    milestone_25_points = fields.Integer(string="25-Class Milestone", default=100)
    milestone_50_points = fields.Integer(string="50-Class Milestone", default=250)
    milestone_100_points = fields.Integer(string="100-Class Milestone", default=500)
    milestone_200_points = fields.Integer(string="200-Class Milestone", default=1000)

    # ── Instructor awards ─────────────────────────────────────────────────
    instructor_award_enabled = fields.Boolean(
        string="Enable Instructor Awards", default=True,
        help="Allow instructors to manually award points to members.",
    )
    max_instructor_award_per_day = fields.Integer(
        string="Daily Cap (pts / member)",
        default=500,
        help=(
            "Maximum points any instructor can award a single member per calendar day. "
            "Set to 0 to remove the cap entirely."
        ),
    )

    # ── Redemption placeholder ────────────────────────────────────────────
    redemption_enabled = fields.Boolean(
        string="Enable Point Redemption (Phase 2)",
        default=False,
        help="Future: allow members to redeem points for rewards. Not yet implemented.",
    )

    @api.model
    def get_singleton(self):
        """Return the single config record, creating it if missing."""
        config = self.search([], limit=1)
        if not config:
            config = self.create({})
        return config
