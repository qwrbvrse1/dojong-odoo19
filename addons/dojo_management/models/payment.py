from odoo import models, fields, api

class DojoPayment(models.Model):
    _name = 'dojo.payment'
    _description = 'Dojo Payment'
    _order = 'payment_date desc'

    student_id = fields.Many2one('dojo.student', string='Student', required=True)
    amount = fields.Float('Amount', required=True)
    payment_date = fields.Date('Payment Date', default=fields.Date.today)
    due_date = fields.Date('Due Date')
    state = fields.Selection([
        ('paid', 'Paid'),
        ('pending', 'Pending'),
        ('late', 'Late'),
    ], string='Status', default='pending')
    notes = fields.Text('Notes')

    def action_mark_paid(self):
        self.write({'state': 'paid'})

    def action_mark_pending(self):
        self.write({'state': 'pending'})

    def action_mark_late(self):
        self.write({'state': 'late'})

    def action_view_student(self):
        return {
            'type': 'ir.actions.act_window',
            'name': f'Student - {self.student_id.name}',
            'res_model': 'dojo.student',
            'view_mode': 'form',
            'res_id': self.student_id.id,
            'target': 'current',
        }

    def check_late_payments(self):
        today = fields.Date.today()
        late_payments = self.search([
            ('due_date', '<', today),
            ('state', '=', 'pending')
        ])
        for payment in late_payments:
            payment.state = 'late'
            # Here you could add notification logic (email, activity, etc.)

    def notify_late_payment(self):
        # Placeholder for notification logic (email, activity, etc.)
        pass

    def write(self, vals):
        res = super().write(vals)
        self.check_late_payments()
        return res

    def create(self, vals):
        record = super().create(vals)
        record.check_late_payments()
        return record
