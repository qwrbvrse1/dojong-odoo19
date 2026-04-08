from odoo import models, fields


class ElevenLabsAgent(models.Model):
    _name = 'dojo.elevenlabs.agent'
    _description = 'ElevenLabs Conversational AI Agent'
    _order = 'name'
    _rec_name = 'name'

    name = fields.Char('Agent Name', required=True)
    elevenlabs_id = fields.Char('ElevenLabs Agent ID', required=True, index=True)
