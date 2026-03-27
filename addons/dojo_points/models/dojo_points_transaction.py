from odoo import fields, models


class DojoPointsTransaction(models.Model):
    """Immutable append-only ledger of all point events for every member.

    Points are always positive — this ledger never decreases a balance.
    The member's total is always derived from SUM(amount) on this table,
    so there is no risk of a stored balance drifting out of sync.
    """

    _name = "dojo.points.transaction"
    _description = "Dojang Points Transaction"
    _order = "date desc, id desc"
    _rec_name = "note"

    member_id = fields.Many2one(
        "dojo.member",
        string="Member",
        required=True,
        index=True,
        ondelete="cascade",
        readonly=True,
    )
    date = fields.Datetime(
        string="Date",
        default=fields.Datetime.now,
        required=True,
        readonly=True,
    )
    source_type = fields.Selection(
        [
            ("attendance", "Class Attendance"),
            ("late_attendance", "Late Attendance"),
            ("streak_bonus", "Streak Bonus"),
            ("belt_promotion", "Belt Promotion"),
            ("attendance_milestone", "Attendance Milestone"),
            ("instructor_award", "Instructor Award"),
            ("adjustment", "Manual Adjustment"),
        ],
        string="Type",
        required=True,
        readonly=True,
    )
    amount = fields.Integer(
        string="Points",
        required=True,
        readonly=True,
        help="Always a positive integer — points are never subtracted in this ledger.",
    )
    note = fields.Char(string="Note", readonly=True)
    streak_length = fields.Integer(
        string="Streak at Award",
        readonly=True,
        help="The streak count when this bonus was triggered (streak_bonus rows only).",
    )
    awarded_by = fields.Many2one(
        "res.users",
        string="Awarded By",
        readonly=True,
        help="Instructor who manually awarded these points.",
    )
    attendance_log_id = fields.Many2one(
        "dojo.attendance.log",
        string="Attendance Log",
        ondelete="set null",
        index=True,
        readonly=True,
    )
    member_rank_id = fields.Many2one(
        "dojo.member.rank",
        string="Rank Record",
        ondelete="set null",
        index=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="member_id.company_id",
        store=True,
        readonly=True,
    )
