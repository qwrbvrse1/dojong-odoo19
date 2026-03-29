from odoo import api, fields, models


class DojoAttendanceLog(models.Model):
    _name = "dojo.attendance.log"
    _description = "Dojang Attendance Log"
    _order = "checkin_datetime desc"
    _rec_name = "name"

    name = fields.Char(compute="_compute_name", store=True, string="Name")

    @api.depends("member_id", "session_id")
    def _compute_name(self):
        for rec in self:
            parts = []
            if rec.member_id:
                parts.append(rec.member_id.name)
            if rec.session_id:
                parts.append(rec.session_id.display_name or rec.session_id.name)
            rec.name = " \u2014 ".join(parts) if parts else "Attendance Log"

    session_id = fields.Many2one(
        "dojo.class.session", required=True, ondelete="cascade", index=True
    )
    enrollment_id = fields.Many2one("dojo.class.enrollment", index=True)
    member_id = fields.Many2one("dojo.member", required=True, index=True, ondelete="cascade")
    status = fields.Selection(
        [
            ("present", "Present"),
            ("late", "Late"),
            ("absent", "Absent"),
            ("excused", "Excused"),
            ("sick", "Sick"),
            ("injury", "Injury"),
            ("vacation", "Vacation"),
            ("other", "Other"),
        ],
        default="present",
        required=True,
    )
    checkin_datetime = fields.Datetime(default=fields.Datetime.now, required=True)
    checkout_datetime = fields.Datetime(string="Checkout Time")
    note = fields.Text()
    company_id = fields.Many2one(
        "res.company", related="session_id.company_id", store=True, readonly=True
    )

    # ── Computed stats ────────────────────────────────────────────────────
    duration_hours = fields.Float(
        string="Duration (Hours)",
        compute="_compute_duration_hours",
        store=True,
        help="Time spent in session, computed from check-in to check-out.",
    )
    is_late = fields.Boolean(
        string="Late Arrival",
        compute="_compute_is_late",
        store=True,
        help="Auto-detected: arrived more than 15 minutes after session start.",
    )
    performance_rating = fields.Selection(
        [
            ("excellent", "Excellent"),
            ("good", "Good"),
            ("average", "Average"),
            ("needs_improvement", "Needs Improvement"),
            ("poor", "Poor"),
        ],
        string="Performance",
    )

    @api.depends("checkin_datetime", "checkout_datetime")
    def _compute_duration_hours(self):
        for rec in self:
            if rec.checkin_datetime and rec.checkout_datetime:
                delta = rec.checkout_datetime - rec.checkin_datetime
                rec.duration_hours = delta.total_seconds() / 3600.0
            else:
                rec.duration_hours = 0.0

    @api.depends("checkin_datetime", "session_id.start_datetime", "status")
    def _compute_is_late(self):
        for rec in self:
            if rec.status == "late":
                rec.is_late = True
            elif rec.checkin_datetime and rec.session_id.start_datetime:
                delta = (rec.checkin_datetime - rec.session_id.start_datetime).total_seconds()
                rec.is_late = delta > 900  # 15 minutes
            else:
                rec.is_late = False

    _dojo_attendance_unique_session_member = models.Constraint(
        "unique(session_id, member_id)",
        "Attendance is already logged for this member in this session.",
    )
