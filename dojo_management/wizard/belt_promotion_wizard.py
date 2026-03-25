from odoo import models, fields, api
from datetime import date

class BeltPromotionWizard(models.TransientModel):
    _name = 'belt.promotion.wizard'
    _description = 'Belt Promotion Wizard'

    student_ids = fields.Many2many('dojo.student', string='Students to Promote', required=True)
    new_belt_level = fields.Selection([
        ('white', 'White Belt'),
        ('yellow', 'Yellow Belt'),
        ('orange', 'Orange Belt'),
        ('green', 'Green Belt'),
        ('blue', 'Blue Belt'),
        ('purple', 'Purple Belt'),
        ('brown', 'Brown Belt'),
        ('black', 'Black Belt'),
    ], string='New Belt Level', required=True)
    promotion_date = fields.Date('Promotion Date', default=fields.Date.today, required=True)
    notes = fields.Text('Promotion Notes')

    def action_promote(self):
        """Promote selected students to new belt level"""
        for student in self.student_ids:
            # Create a message in the chatter about the promotion
            old_belt = dict(student._fields['belt_level'].selection).get(student.belt_level)
            new_belt = dict(self._fields['new_belt_level'].selection).get(self.new_belt_level)
            promotion_message = f"🏆 Promoted from {old_belt} to {new_belt}"
            if self.notes:
                promotion_message += f"\n\nNotes: {self.notes}"
            
            # Update student record
            student.write({
                'belt_level': self.new_belt_level,
                'promotion_date': self.promotion_date,
            })
            
            # If promoting to black belt, set dan rank to 1
            if self.new_belt_level == 'black' and student.belt_level != 'black':
                student.belt_rank = '1'
            
            # Post message to chatter
            student.message_post(
                body=promotion_message,
                subject='Belt Promotion',
                message_type='notification',
            )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success!',
                'message': f'{len(self.student_ids)} student(s) promoted successfully!',
                'type': 'success',
                'sticky': False,
            }
        }
