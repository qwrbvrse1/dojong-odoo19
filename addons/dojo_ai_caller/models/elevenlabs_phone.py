from odoo import models, fields, api


class ElevenLabsPhone(models.Model):
    _name = 'dojo.elevenlabs.phone'
    _description = 'ElevenLabs Phone Number'
    _order = 'phone_number'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name', store=True)
    elevenlabs_id = fields.Char('ElevenLabs Phone ID', required=True, index=True)
    phone_number = fields.Char('Phone Number')
    provider = fields.Char('Provider')

    @api.depends('phone_number', 'elevenlabs_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec.phone_number or rec.elevenlabs_id
