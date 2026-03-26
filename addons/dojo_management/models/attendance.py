from odoo import models, fields, api
from datetime import datetime, timedelta

class DojoAttendance(models.Model):
    _name = 'dojo.attendance'
    _description = 'Dojo Attendance'
    _order = 'date desc, student_id'

    student_id = fields.Many2one('dojo.student', string='Student', required=True)
    session_id = fields.Many2one('dojo.session', string='Session', required=True)
    date = fields.Date('Attendance Date', default=fields.Date.today)
    
    # Enhanced status options
    status = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused'),
        ('sick', 'Sick'),
        ('injury', 'Injury'),
        ('vacation', 'Vacation'),
        ('other', 'Other'),
    ], string='Status', default='present', required=True)
    
    # Additional tracking fields
    arrival_time = fields.Float('Arrival Time', help='Time in 24-hour format (e.g., 14.5 for 2:30 PM)')
    departure_time = fields.Float('Departure Time', help='Time in 24-hour format (e.g., 16.0 for 4:00 PM)')
    duration_hours = fields.Float('Duration (Hours)', compute='_compute_duration', store=True)
    
    # Performance tracking
    performance_rating = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('average', 'Average'),
        ('needs_improvement', 'Needs Improvement'),
        ('poor', 'Poor'),
    ], string='Performance Rating')
    
    belt_level = fields.Many2one('dojo.belt_rank', string='Belt Level', related='student_id.belt_level_id', readonly=True, store=True)
    
    notes = fields.Text('Notes')
    
    # Computed fields for reporting
    is_late = fields.Boolean('Late', compute='_compute_late_status', store=True)
    attendance_streak = fields.Integer('Attendance Streak', compute='_compute_attendance_streak')
    
    _sql_constraints = [
        ('unique_attendance_per_student_session', 'unique(student_id, session_id)', 'Attendance for this student and session already exists!'),
    ]

    @api.depends('arrival_time', 'departure_time')
    def _compute_duration(self):
        for attendance in self:
            if attendance.arrival_time and attendance.departure_time:
                attendance.duration_hours = attendance.departure_time - attendance.arrival_time
            else:
                attendance.duration_hours = 0.0

    @api.depends('status', 'arrival_time', 'session_id.start_time')
    def _compute_late_status(self):
        for attendance in self:
            if attendance.status == 'late':
                attendance.is_late = True
            elif attendance.arrival_time and attendance.session_id.start_time:
                # Consider late if arrival is more than 15 minutes after start time
                late_threshold = attendance.session_id.start_time + 0.25  # 15 minutes
                attendance.is_late = attendance.arrival_time > late_threshold
            else:
                attendance.is_late = False

    @api.depends('student_id', 'date')
    def _compute_attendance_streak(self):
        for attendance in self:
            if not attendance.student_id:
                attendance.attendance_streak = 0
                continue
                
            # Get all attendances for this student, ordered by date
            student_attendances = self.search([
                ('student_id', '=', attendance.student_id.id),
                ('status', 'in', ['present', 'late']),
                ('date', '<=', attendance.date)
            ], order='date desc')
            
            streak = 0
            current_date = attendance.date
            
            for att in student_attendances:
                if att.status in ['present', 'late']:
                    # Check if this is consecutive
                    if streak == 0 or (current_date - att.date).days == 1:
                        streak += 1
                        current_date = att.date
                    else:
                        break
                else:
                    break
            
            attendance.attendance_streak = streak

    @api.model
    def get_attendance_stats(self, student_id=None, start_date=None, end_date=None):
        """Get attendance statistics for reporting"""
        domain = []
        if student_id:
            domain.append(('student_id', '=', student_id))
        if start_date:
            domain.append(('date', '>=', start_date))
        if end_date:
            domain.append(('date', '<=', end_date))
            
        attendances = self.search(domain)
        
        stats = {
            'total': len(attendances),
            'present': len(attendances.filtered(lambda a: a.status == 'present')),
            'absent': len(attendances.filtered(lambda a: a.status == 'absent')),
            'late': len(attendances.filtered(lambda a: a.status == 'late')),
            'excused': len(attendances.filtered(lambda a: a.status == 'excused')),
            'sick': len(attendances.filtered(lambda a: a.status == 'sick')),
            'injury': len(attendances.filtered(lambda a: a.status == 'injury')),
            'vacation': len(attendances.filtered(lambda a: a.status == 'vacation')),
            'other': len(attendances.filtered(lambda a: a.status == 'other')),
        }
        
        stats['attendance_rate'] = (stats['present'] / stats['total'] * 100) if stats['total'] else 0
        stats['late_rate'] = (stats['late'] / stats['total'] * 100) if stats['total'] else 0
        
        return stats

    def action_mark_present(self):
        self.write({'status': 'present'})

    def action_mark_absent(self):
        self.write({'status': 'absent'})

    def action_mark_late(self):
        self.write({'status': 'late'})

    def action_mark_excused(self):
        self.write({'status': 'excused'})

    def action_view_student(self):
        return {
            'type': 'ir.actions.act_window',
            'name': f'Student - {self.student_id.name}',
            'res_model': 'dojo.student',
            'view_mode': 'form',
            'res_id': self.student_id.id,
            'target': 'current',
        }

    def action_view_session(self):
        return {
            'type': 'ir.actions.act_window',
            'name': f'Session - {self.session_id.name}',
            'res_model': 'dojo.session',
            'view_mode': 'form',
            'res_id': self.session_id.id,
            'target': 'current',
        }
