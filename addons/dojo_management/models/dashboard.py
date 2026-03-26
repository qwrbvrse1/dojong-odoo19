from odoo import models, fields, api
from datetime import date

class DojoDashboard(models.TransientModel):
    _name = 'dojo.dashboard'
    _description = 'Dojo Dashboard'

    student_count = fields.Integer(string='Total Students', compute='_compute_stats')
    payment_count = fields.Integer(string='Total Payments', compute='_compute_stats')
    attendance_count = fields.Integer(string='Total Attendances', compute='_compute_stats')
    students_this_month = fields.Integer(string='New Students This Month', compute='_compute_stats')
    payments_this_month = fields.Float(string='Payments This Month', compute='_compute_stats')
    late_payments = fields.Integer(string='Late Payments', compute='_compute_stats')
    attendance_rate = fields.Float(string='Attendance Rate (%)', compute='_compute_stats')
    
    # Dynamic Lists for Stats
    belt_stat_ids = fields.One2many('dojo.dashboard.belt.stat', 'dashboard_id', string='Belt Stats', compute='_compute_stats')
    style_stat_ids = fields.One2many('dojo.dashboard.style.stat', 'dashboard_id', string='Style Stats', compute='_compute_stats')

    def _compute_stats(self):
        Student = self.env['dojo.student']
        Payment = self.env['dojo.payment']
        Attendance = self.env['dojo.attendance']
        BeltRank = self.env['dojo.belt_rank']
        Style = self.env['dojo.martial_arts_style']
        
        today = date.today()
        month_start = today.replace(day=1)
        
        # Main stats
        self.student_count = Student.search_count([])
        self.payment_count = Payment.search_count([])
        self.attendance_count = Attendance.search_count([])
        self.students_this_month = Student.search_count([('enrollment_date', '>=', month_start)])
        self.payments_this_month = sum(Payment.search([('payment_date', '>=', month_start)]).mapped('amount'))
        self.late_payments = Payment.search_count([('state', '=', 'late')])
        
        total_attendances = Attendance.search_count([])
        present_attendances = Attendance.search_count([('status', '=', 'present')])
        self.attendance_rate = (present_attendances / total_attendances * 100) if total_attendances else 0
        
        # Compute Belt Stats
        belt_stats = []
        # Get all configured belts
        belts = BeltRank.search([], order='style_id, sequence asc')
        for belt in belts:
            count = Student.search_count([('belt_level_id', '=', belt.id)])
            if count > 0:
                # Calculate text color based on background color
                bg_color = belt.color or '#808080'
                # Simple brightness formula
                r = int(bg_color[1:3], 16)
                g = int(bg_color[3:5], 16)
                b = int(bg_color[5:7], 16)
                brightness = (r * 299 + g * 587 + b * 114) / 1000
                text_color = '#ffffff' if brightness < 128 else '#1f2937'
                
                belt_stats.append((0, 0, {
                    'name': belt.name,
                    'style_name': belt.style_id.name,
                    'count': count,
                    'color': bg_color,
                    'text_color': text_color,
                    'icon': belt.icon
                }))
        self.belt_stat_ids = belt_stats
        
        # Compute Style Stats
        style_stats = []
        styles = Style.search([])
        for style in styles:
            count = Student.search_count([('martial_arts_style_id', '=', style.id)])
            style_stats.append((0, 0, {
                'name': style.name,
                'count': count,
                'code': style.code
            }))
        self.style_stat_ids = style_stats

    def action_view_students(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Students',
            'res_model': 'dojo.student',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_view_payments(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payments',
            'res_model': 'dojo.payment',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_view_attendance(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Attendance',
            'res_model': 'dojo.attendance',
            'view_mode': 'tree,form',
            'target': 'current',
        }

class DojoDashboardBeltStat(models.TransientModel):
    _name = 'dojo.dashboard.belt.stat'
    _description = 'Dashboard Belt Statistics'
    
    dashboard_id = fields.Many2one('dojo.dashboard')
    name = fields.Char('Belt Name')
    style_name = fields.Char('Style Name')
    count = fields.Integer('Student Count')
    color = fields.Char('Belt Color') # Hex code
    text_color = fields.Char('Text Color') # Calculated for contrast
    icon = fields.Char('Icon')

class DojoDashboardStyleStat(models.TransientModel):
    _name = 'dojo.dashboard.style.stat'
    _description = 'Dashboard Style Statistics'
    
    dashboard_id = fields.Many2one('dojo.dashboard')
    name = fields.Char('Style Name')
    count = fields.Integer('Student Count')
    code = fields.Char('Style Code')
