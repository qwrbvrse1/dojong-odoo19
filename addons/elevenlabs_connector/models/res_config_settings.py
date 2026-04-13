# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    """Add ElevenLabs configuration to main Settings page."""
    _inherit = 'res.config.settings'

    # ElevenLabs Configuration
    elevenlabs_api_key = fields.Char(
        string='ElevenLabs API Key',
        config_parameter='elevenlabs_connector.api_key',
        help='Your ElevenLabs API key. Get it from https://elevenlabs.io/app/settings/api-keys',
    )
    
    elevenlabs_voice_id = fields.Char(
        string='Default Voice ID',
        config_parameter='elevenlabs_connector.voice_id',
        default='21m00Tcm4TlvDq8ikWAM',  # Default ElevenLabs voice
        help='ElevenLabs voice model ID. Default: Rachel (21m00Tcm4TlvDq8ikWAM)',
    )
    
    elevenlabs_language = fields.Selection(
        [
            ('en', 'English'),
            ('es', 'Spanish'),
            ('fr', 'French'),
            ('de', 'German'),
            ('it', 'Italian'),
            ('pt', 'Portuguese'),
            ('pl', 'Polish'),
            ('tr', 'Turkish'),
            ('ru', 'Russian'),
            ('nl', 'Dutch'),
            ('cs', 'Czech'),
            ('ar', 'Arabic'),
            ('zh', 'Chinese'),
            ('ja', 'Japanese'),
            ('hu', 'Hungarian'),
            ('ko', 'Korean'),
        ],
        string='Language',
        config_parameter='elevenlabs_connector.language',
        default='en',
        help='Language for voice output',
    )
    
    # AI Provider Configuration
    ai_provider = fields.Selection(
        [
            ('openai', 'OpenAI'),
            ('gemini', 'Google Gemini'),
            ('odoo_native', 'Odoo Native AI'),
            ('custom', 'Custom Provider'),
        ],
        string='AI Provider',
        config_parameter='elevenlabs_connector.ai_provider',
        default='openai',
        help='Select the AI provider for processing voice queries',
    )
    
    openai_api_key = fields.Char(
        string='OpenAI API Key',
        config_parameter='elevenlabs_connector.openai_api_key',
        help='Your OpenAI API key. Get it from https://platform.openai.com/api-keys',
    )
    
    gemini_api_key = fields.Char(
        string='Gemini API Key',
        config_parameter='elevenlabs_connector.gemini_api_key',
        help='Your Google Gemini API key. Get it from https://makersuite.google.com/app/apikey',
    )
    
    # Test Connection
    elevenlabs_connection_status = fields.Char(
        string='Connection Status',
        readonly=True,
        help='Status of the last connection test to ElevenLabs API',
    )

    # Voice picker — transient display-only; actual selection stored in elevenlabs_voice_id
    elevenlabs_available_voices = fields.Text(
        string='Available Voices (JSON)',
        help='JSON list of voices fetched from ElevenLabs. Populated by "Load Voices" button.',
    )

    def action_fetch_elevenlabs_voices(self):
        """Fetch available voices from ElevenLabs and store them for the voice picker."""
        self.ensure_one()
        api_key = self.elevenlabs_api_key or self.env['ir.config_parameter'].sudo().get_str('elevenlabs_connector.api_key')
        if not api_key:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No API Key',
                    'message': 'Please enter your ElevenLabs API key first.',
                    'type': 'warning',
                    'sticky': False,
                }
            }
        try:
            service = self.env['elevenlabs.service']
            voices = service.get_voices(api_key=api_key)
            import json
            self.env['ir.config_parameter'].sudo().set_str(
                'elevenlabs_connector.available_voices',
                json.dumps(voices),
            )
            count = len(voices)
            # Re-open the settings form so the Selection field
            # re-computes its choices from the freshly-saved param.
            action = self.env['ir.actions.act_window']._for_xml_id(
                'base_setup.action_general_configuration'
            )
            action['target'] = 'main'
            return action
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Failed to Load Voices',
                    'message': str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def _get_elevenlabs_voice_selection(self):
        """Return Selection values from the cached voice list."""
        import json
        raw = self.env['ir.config_parameter'].sudo().get_str('elevenlabs_connector.available_voices') or '[]'
        try:
            voices = json.loads(raw)
        except Exception:
            voices = []
        result = [(v['voice_id'], f"{v['name']} ({v['category']})" if v.get('category') else v['name']) for v in voices if v.get('voice_id')]
        if not result:
            result = [('21m00Tcm4TlvDq8ikWAM', 'Rachel — premade (load voices to see more)')]
        return result

    elevenlabs_voice_select = fields.Selection(
        selection='_get_elevenlabs_voice_selection',
        string='Voice',
        help='Select a voice. Click "Load Voices" first to populate this list.',
    )

    @api.onchange('elevenlabs_voice_select')
    def _onchange_elevenlabs_voice_select(self):
        if self.elevenlabs_voice_select:
            self.elevenlabs_voice_id = self.elevenlabs_voice_select

    def action_test_elevenlabs_connection(self):
        """Test connection to ElevenLabs API"""
        self.ensure_one()
        if not self.elevenlabs_api_key:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': 'Please enter an API key first',
                    'type': 'danger',
                    'sticky': True,
                }
            }
        
        try:
            service = self.env['elevenlabs.service']
            result = service.test_connection(self.elevenlabs_api_key)
            if result:
                self.elevenlabs_connection_status = 'Connected successfully'
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Success',
                        'message': 'ElevenLabs API connection successful',
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                raise ValidationError('Connection test failed - Invalid API key or network error')
        except UserError as e:
            _logger.error('ElevenLabs connection test failed: %s', str(e))
            self.elevenlabs_connection_status = f'Error: {str(e)}'
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Connection Failed',
                    'message': f'Failed to connect to ElevenLabs: {str(e)}',
                    'type': 'danger',
                    'sticky': True,
                }
            }
        except Exception as e:
            _logger.error('ElevenLabs connection test failed: %s', str(e), exc_info=True)
            self.elevenlabs_connection_status = f'Error: {str(e)}'
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Connection Failed',
                    'message': f'Failed to connect to ElevenLabs: {str(e)}',
                    'type': 'danger',
                    'sticky': True,
                }
            }

