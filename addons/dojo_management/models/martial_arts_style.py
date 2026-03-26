from odoo import models, fields, api

class MartialArtsStyle(models.Model):
    _name = 'dojo.martial_arts_style'
    _description = 'Martial Arts Style'
    _order = 'name'

    name = fields.Char('Style Name', required=True)
    code = fields.Char('Code', required=True, help='Unique identifier for this style')
    description = fields.Text('Description')
    belt_rank_ids = fields.One2many('dojo.belt_rank', 'style_id', string='Belt Ranks')
    belt_count = fields.Integer('Number of Belts', compute='_compute_belt_count')
    student_count = fields.Integer('Number of Students', compute='_compute_student_count')
    active = fields.Boolean('Active', default=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Style code must be unique!')
    ]

    @api.depends('belt_rank_ids')
    def _compute_belt_count(self):
        for style in self:
            style.belt_count = len(style.belt_rank_ids)

    def _compute_student_count(self):
        for style in self:
            style.student_count = self.env['dojo.student'].search_count([('martial_arts_style_id', '=', style.id)])


class BeltRank(models.Model):
    _name = 'dojo.belt_rank'
    _description = 'Belt Rank'
    _order = 'style_id, sequence, id'

    name = fields.Char('Belt Name', required=True)
    color = fields.Char('Color Code', help='Hex color code for display')
    sequence = fields.Integer('Sequence', default=10, help='Order in belt progression')
    style_id = fields.Many2one('dojo.martial_arts_style', string='Martial Arts Style', required=True, ondelete='cascade')
    has_dan_ranks = fields.Boolean('Has Dan Ranks', default=False, help='Check if this belt has Dan levels (typically black belt)')
    icon = fields.Char('Icon', default='🥋', help='Emoji icon for display')
    active = fields.Boolean('Active', default=True)

    _sql_constraints = [
        ('sequence_style_unique', 'unique(style_id, sequence)', 'Sequence must be unique within a style!')
    ]

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.icon} {record.name}"
            result.append((record.id, name))
        return result
