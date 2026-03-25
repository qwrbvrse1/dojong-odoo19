from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime, timedelta

class DojoStudent(models.Model):
    _name = 'dojo.student'
    _description = 'Dojo Student'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char('Student Name', required=True, tracking=True)
    photo = fields.Image('Photo', max_width=256, max_height=256)
    dob = fields.Date('Date of Birth')
    email = fields.Char('Email')
    phone = fields.Char('Phone')
    enrollment_date = fields.Date('Enrollment Date', default=fields.Date.today)
    active = fields.Boolean('Active', default=True)
    
    # Martial Arts Style - Now configurable
    martial_arts_style_id = fields.Many2one('dojo.martial_arts_style', string='Martial Arts Style', tracking=True, ondelete='restrict')
    
    # Belt and rank information - Now configurable
    belt_level_id = fields.Many2one('dojo.belt_rank', string='Current Belt Level', tracking=True, ondelete='restrict')
    
    belt_rank = fields.Selection([
        ('0', 'No Dan'),
        ('1', '1st Dan'),
        ('2', '2nd Dan'),
        ('3', '3rd Dan'),
        ('4', '4th Dan'),
        ('5', '5th Dan'),
        ('6', '6th Dan'),
        ('7', '7th Dan'),
        ('8', '8th Dan'),
        ('9', '9th Dan'),
        ('10', '10th Dan'),
    ], string='Dan Rank', default='0', help='Dan rank for black belts (1-10)', tracking=True)
    promotion_date = fields.Date('Last Promotion Date')
    next_promotion_date = fields.Date('Next Promotion Date', compute='_compute_next_promotion')
    
    # Personal information
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string='Gender')
    
    address = fields.Text('Address')
    emergency_contact = fields.Char('Emergency Contact')
    emergency_phone = fields.Char('Emergency Phone')
    medical_conditions = fields.Text('Medical Conditions')
    
    # Performance tracking
    total_sessions = fields.Integer('Total Sessions', compute='_compute_performance_stats')
    attendance_rate = fields.Float('Attendance Rate (%)', compute='_compute_performance_stats', store=True)
    current_streak = fields.Integer('Current Attendance Streak', compute='_compute_performance_stats')
    longest_streak = fields.Integer('Longest Attendance Streak', compute='_compute_performance_stats')
    average_performance = fields.Float('Average Performance Rating', compute='_compute_performance_stats')
    
    # Financial tracking
    total_paid = fields.Float('Total Paid', compute='_compute_financial_stats')
    outstanding_balance = fields.Float('Outstanding Balance', compute='_compute_financial_stats')
    payment_status = fields.Selection([
        ('current', 'Current'),
        ('late', 'Late'),
        ('overdue', 'Overdue'),
        ('suspended', 'Suspended'),
    ], string='Payment Status', default='current', compute='_compute_financial_stats', store=True)
    
    # Relationships
    payment_ids = fields.One2many('dojo.payment', 'student_id', string='Payments')
    attendance_ids = fields.One2many('dojo.attendance', 'student_id', string='Attendance')
    session_ids = fields.Many2many('dojo.session', string='Enrolled Sessions')

    @api.depends('attendance_ids')
    def _compute_performance_stats(self):
        for student in self:
            attendances = student.attendance_ids
            student.total_sessions = len(attendances)
            
            if attendances:
                present_count = len(attendances.filtered(lambda a: a.status in ['present', 'late']))
                student.attendance_rate = (present_count / student.total_sessions) * 100
                
                # Calculate current streak
                recent_attendances = attendances.sorted('date', reverse=True)
                current_streak = 0
                for att in recent_attendances:
                    if att.status in ['present', 'late']:
                        current_streak += 1
                    else:
                        break
                student.current_streak = current_streak
                
                # Calculate longest streak
                longest_streak = 0
                temp_streak = 0
                for att in attendances.sorted('date'):
                    if att.status in ['present', 'late']:
                        temp_streak += 1
                        longest_streak = max(longest_streak, temp_streak)
                    else:
                        temp_streak = 0
                student.longest_streak = longest_streak
                
                # Calculate average performance
                performance_attendances = attendances.filtered(lambda a: a.performance_rating)
                if performance_attendances:
                    ratings = {
                        'excellent': 5,
                        'good': 4,
                        'average': 3,
                        'needs_improvement': 2,
                        'poor': 1
                    }
                    total_rating = sum(ratings.get(att.performance_rating, 0) for att in performance_attendances)
                    student.average_performance = total_rating / len(performance_attendances)
                else:
                    student.average_performance = 0.0
            else:
                student.attendance_rate = 0.0
                student.current_streak = 0
                student.longest_streak = 0
                student.average_performance = 0.0

    @api.depends('payment_ids')
    def _compute_financial_stats(self):
        for student in self:
            payments = student.payment_ids
            student.total_paid = sum(payments.filtered(lambda p: p.state == 'paid').mapped('amount'))
            
            # Calculate outstanding balance
            total_due = sum(payments.filtered(lambda p: p.state in ['pending', 'late']).mapped('amount'))
            student.outstanding_balance = total_due
            
            # Determine payment status
            if student.outstanding_balance == 0:
                student.payment_status = 'current'
            elif student.outstanding_balance > 0:
                overdue_payments = payments.filtered(lambda p: p.state == 'late')
                if overdue_payments:
                    student.payment_status = 'overdue'
                else:
                    student.payment_status = 'late'
            else:
                student.payment_status = 'suspended'

    @api.depends('promotion_date', 'belt_level_id')
    def _compute_next_promotion(self):
        for student in self:
            if student.promotion_date and student.belt_level_id:
                # Default promotion interval: 6 months (approx 180 days)
                # TODO: Add 'promotion_interval' field to dojo.belt_rank model for per-belt logic
                next_date = student.promotion_date + timedelta(days=180)
                student.next_promotion_date = next_date
            else:
                student.next_promotion_date = False

    def action_promote_belt(self):
        """Promote student to next belt level based on sequence"""
        self.ensure_one()
        if not self.martial_arts_style_id:
            raise UserError('Please select a Martial Arts Style first.')
            
        current_seq = self.belt_level_id.sequence if self.belt_level_id else -1
        
        # Find next belt in the same style
        next_belt = self.env['dojo.belt_rank'].search([
            ('style_id', '=', self.martial_arts_style_id.id),
            ('sequence', '>', current_seq),
        ], order='sequence asc', limit=1)
        
        if next_belt:
            self.write({
                'belt_level_id': next_belt.id,
                'promotion_date': fields.Date.today(),
            })
            
            # Message in chatter
            self.message_post(body=f"🏆 Promoted to {next_belt.name}!")
            
            # Handle Dan Ranks if applicable
            if next_belt.has_dan_ranks:
                if self.belt_rank == '0':
                    self.belt_rank = '1' # First Dan
        elif self.belt_level_id.has_dan_ranks:
             # Already at highest belt (Black), maybe increment Dan?
             current_dan = int(self.belt_rank) if self.belt_rank else 0
             if current_dan < 10:
                 self.belt_rank = str(current_dan + 1)
                 self.message_post(body=f"🏆 Promoted to {self.belt_rank}th Dan!")
        else:
             raise UserError("This student is already at the highest belt rank for this style!")

    def action_view_attendance(self):
        return {
            'type': 'ir.actions.act_window',
            'name': f'Attendance - {self.name}',
            'res_model': 'dojo.attendance',
            'view_mode': 'list,form',
            'domain': [('student_id', '=', self.id)],
            'target': 'current',
        }

    def action_view_payments(self):
        return {
            'type': 'ir.actions.act_window',
            'name': f'Payments - {self.name}',
            'res_model': 'dojo.payment',
            'view_mode': 'list,form',
            'domain': [('student_id', '=', self.id)],
            'target': 'current',
        }
    
