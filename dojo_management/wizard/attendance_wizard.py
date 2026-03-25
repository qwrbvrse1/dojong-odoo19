from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AttendanceWizard(models.TransientModel):
    _name = 'attendance.wizard'
    _description = 'Batch Attendance Wizard'

    session_id = fields.Many2one('dojo.session', string='Session', required=True)
    attendance_lines = fields.One2many('attendance.wizard.line', 'wizard_id', string='Attendance Lines')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        session_id = self._context.get('default_session_id') or self._context.get('active_id')
        if not session_id:
            raise UserError(_('No session selected for attendance.'))
        session = self.env['dojo.session'].browse(session_id)
        res['session_id'] = session.id
        if not session.student_ids:
            raise UserError(_('No students found for this session.'))
        lines = []
        for student in session.student_ids:
            lines.append((0, 0, {
                'student_id': student.id,
                'status': 'present',
            }))
        res['attendance_lines'] = lines
        return res

    def action_confirm(self):
        for line in self.attendance_lines:
            self.env['dojo.attendance'].create({
                'student_id': line.student_id.id,
                'session_id': self.session_id.id,
                'date': fields.Date.today(),
                'status': line.status,
            })
        return {'type': 'ir.actions.act_window_close'}

class AttendanceWizardLine(models.TransientModel):
    _name = 'attendance.wizard.line'
    _description = 'Attendance Wizard Line'

    wizard_id = fields.Many2one('attendance.wizard', string='Wizard')
    student_id = fields.Many2one('dojo.student', string='Student', required=True)
    status = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
    ], string='Status', default='present')
