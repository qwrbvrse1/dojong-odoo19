from odoo import api, fields, models


class DojoMartialArtStyle(models.Model):
    _name = "dojo.martial.art.style"
    _description = "Martial Art Style"
    _order = "sequence, name"

    _sql_constraints = [
        ("unique_code", "unique(code, company_id)", "The code must be unique per company."),
    ]

    name = fields.Char(required=True, string="Style Name")
    code = fields.Char(string="Code", help="Short code, e.g. BJJ, MT, JDO")
    sequence = fields.Integer(default=10)
    description = fields.Text(string="Description")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, index=True
    )

    # ── Related records ────────────────────────────────────────────────────
    program_ids = fields.One2many("dojo.program", "style_id", string="Programs")
    belt_rank_ids = fields.One2many(
        "dojo.belt.rank", "style_id", string="Belt Ranks"
    )

    # ── Computed stats ────────────────────────────────────────────────────
    belt_count = fields.Integer(
        compute="_compute_belt_count", string="Number of Belts",
    )
    student_count = fields.Integer(
        compute="_compute_student_count", string="Number of Students",
    )

    @api.depends("belt_rank_ids")
    def _compute_belt_count(self):
        for style in self:
            style.belt_count = len(style.belt_rank_ids)

    def _compute_student_count(self):
        for style in self:
            programs = style.program_ids
            if not programs:
                style.student_count = 0
                continue
            templates = self.env["dojo.class.template"].search([
                ("program_id", "in", programs.ids),
            ])
            enrollments = self.env["dojo.class.enrollment"].search([
                ("session_id.template_id", "in", templates.ids),
            ])
            style.student_count = len(enrollments.mapped("member_id"))
