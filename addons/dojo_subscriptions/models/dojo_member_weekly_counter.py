"""Extensions to dojo.member for enrolled courses."""
from odoo import fields, models


class DojoMemberWeeklyCounter(models.Model):
    _inherit = "dojo.member"

    # Reverse side of the dojo_class_template_member_rel M2M — courses this member
    # is explicitly enrolled in (course roster).
    enrolled_template_ids = fields.Many2many(
        "dojo.class.template",
        "dojo_class_template_member_rel",
        "member_id",    # this member's FK column in the rel table
        "template_id",  # the template FK column
        string="Enrolled Courses",
        readonly=True,
    )
