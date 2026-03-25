from odoo import models, fields, api
from datetime import datetime, timedelta
import calendar

class DojoSession(models.Model):
    _name = 'dojo.session'
    _description = 'Dojo Session'
    _order = 'date desc'

    name = fields.Char('Session Name', required=True)
    date = fields.Datetime('Session Date', required=True, default=fields.Datetime.now)
    instructor_id = fields.Many2one('res.users', string='Instructor')
    student_ids = fields.Many2many('dojo.student', string='Expected Students')
    notes = fields.Text('Notes')
    
    # Recurring session fields
    is_recurring = fields.Boolean('Recurring Session', default=False)
    recurring_days = fields.Selection([
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ], string='Recurring Day', help='Select the day of the week for recurring sessions')
    
    start_time = fields.Float('Start Time', help='Time in 24-hour format (e.g., 14.5 for 2:30 PM)')
    end_time = fields.Float('End Time', help='Time in 24-hour format (e.g., 16.0 for 4:00 PM)')
    session_type = fields.Selection([
        ('regular', 'Regular Training'),
        ('advanced', 'Advanced Training'),
        ('beginner', 'Beginner Class'),
        ('sparring', 'Sparring Session'),
        ('competition', 'Competition Training'),
        ('special', 'Special Event'),
    ], string='Session Type', default='regular')
    
    max_students = fields.Integer('Maximum Students', default=20)
    current_enrollment = fields.Integer('Current Enrollment', compute='_compute_current_enrollment')
    is_full = fields.Boolean('Session Full', compute='_compute_current_enrollment')
    
    # Status fields
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft')
    
    # Attendance tracking
    attendance_ids = fields.One2many('dojo.attendance', 'session_id', string='Attendance Records')
    attendance_count = fields.Integer('Attendance Count', compute='_compute_attendance_stats')
    present_count = fields.Integer('Present Count', compute='_compute_attendance_stats')
    absent_count = fields.Integer('Absent Count', compute='_compute_attendance_stats')
    attendance_rate = fields.Float('Attendance Rate (%)', compute='_compute_attendance_stats')

    @api.depends('student_ids')
    def _compute_current_enrollment(self):
        for session in self:
            session.current_enrollment = len(session.student_ids)
            session.is_full = session.current_enrollment >= session.max_students

    @api.depends('attendance_ids')
    def _compute_attendance_stats(self):
        for session in self:
            attendances = session.attendance_ids
            session.attendance_count = len(attendances)
            session.present_count = len(attendances.filtered(lambda a: a.status == 'present'))
            session.absent_count = len(attendances.filtered(lambda a: a.status == 'absent'))
            session.attendance_rate = (session.present_count / session.attendance_count * 100) if session.attendance_count else 0

    def action_confirm_session(self):
        self.write({'state': 'confirmed'})

    def action_start_session(self):
        self.write({'state': 'in_progress'})

    def action_complete_session(self):
        self.write({'state': 'completed'})

    def action_cancel_session(self):
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    @api.model
    def create_recurring_sessions(self, start_date, end_date, recurring_days, start_time, end_time, session_type, instructor_id, name_template):
        """Create recurring sessions for the specified period"""
        sessions = []
        current_date = start_date
        
        while current_date <= end_date:
            day_name = current_date.strftime('%A').lower()
            if day_name in recurring_days:
                # Create session for this day
                session_date = datetime.combine(current_date, datetime.min.time())
                session_date = session_date.replace(hour=int(start_time), minute=int((start_time % 1) * 60))
                
                session_name = f"{name_template} - {current_date.strftime('%A, %B %d, %Y')}"
                
                session = self.create({
                    'name': session_name,
                    'date': session_date,
                    'instructor_id': instructor_id,
                    'session_type': session_type,
                    'start_time': start_time,
                    'end_time': end_time,
                    'is_recurring': True,
                    'recurring_days': day_name,
                    'state': 'confirmed',
                })
                sessions.append(session)
            
            current_date += timedelta(days=1)
        
        return sessions

    def open_attendance_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'attendance.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_session_id': self.id},
            'name': 'Batch Attendance',
            'view_id': self.env.ref('dojo_management.view_attendance_wizard_form').id,
        }

    def action_view_attendance(self):
        return {
            'type': 'ir.actions.act_window',
            'name': f'Attendance - {self.name}',
            'res_model': 'dojo.attendance',
            'view_mode': 'list,form',
            'domain': [('session_id', '=', self.id)],
            'target': 'current',
        }
