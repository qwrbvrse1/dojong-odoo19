from odoo import fields, models


class DojoKioskActionLog(models.Model):
    _name = "dojo.kiosk.action.log"
    _description = "Kiosk Action Log"
    _order = "create_date desc"

    config_id = fields.Many2one(
        "dojo.kiosk.config",
        string="Kiosk Config",
        required=True,
        index=True,
        ondelete="cascade",
    )
    action = fields.Char(
        string="Action",
        required=True,
        index=True,
        help="Action type: checkin, checkout, attendance_mark, roster_add, roster_remove, onboarding_action",
    )
    member_id = fields.Many2one(
        "dojo.member",
        string="Member",
        index=True,
        ondelete="set null",
    )
    session_id = fields.Many2one(
        "dojo.class.session",
        string="Session",
        index=True,
        ondelete="set null",
    )
    is_instructor_action = fields.Boolean(
        string="Instructor Action",
        default=False,
        index=True,
        help="True if action was performed via instructor mode",
    )
    summary = fields.Text(string="Summary")
    create_date = fields.Datetime(string="Date", readonly=True)
