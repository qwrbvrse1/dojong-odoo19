import json
import logging
import requests

from odoo import models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

ELEVENLABS_BASE = 'https://api.elevenlabs.io'


class ElevenLabsCaller(models.AbstractModel):
    _name = 'dojo.elevenlabs.caller'
    _description = 'ElevenLabs Conversational AI Caller'

    # ── Internal helpers ─────────────────────────────────
    def _get_api_key(self):
        # 1. Per-campaign key passed via context
        key = self.env.context.get('elevenlabs_api_key')
        if key:
            return key
        # 2. Connect module settings (primary)
        try:
            key = self.env['connect.settings'].sudo().get_param('elevenlabs_api_key')
        except Exception:
            key = False
        if key:
            return key
        # 3. Module-level default (legacy)
        key = self.env['ir.config_parameter'].sudo().get_str(
            'dojo_ai_caller.api_key',
        )
        if key:
            return key
        # 4. Fall back to elevenlabs_connector key
        key = self.env['ir.config_parameter'].sudo().get_str(
            'elevenlabs_connector.api_key',
        )
        if not key:
            raise UserError(_(
                'ElevenLabs API key not configured. '
                'Set it in Connect → Settings → API Keys → ElevenLabs.'
            ))
        return key

    def _make_request(self, method, path, payload=None, timeout=30):
        url = f'{ELEVENLABS_BASE}{path}'
        headers = {
            'xi-api-key': self._get_api_key(),
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        kwargs = {'headers': headers, 'timeout': timeout}
        if payload is not None:
            kwargs['data'] = json.dumps(payload, ensure_ascii=False).encode('utf-8')

        try:
            resp = requests.request(method, url, **kwargs)
            resp.raise_for_status()
            if resp.content:
                return resp.json()
            return {}
        except requests.exceptions.HTTPError as exc:
            body = ''
            if exc.response is not None:
                try:
                    body = exc.response.text[:500]
                except Exception:
                    body = str(exc)
            _logger.error('ElevenLabs API %s %s → %s', method, path, body)
            raise UserError(
                _('ElevenLabs API error: %s') % (body or str(exc))
            ) from exc
        except requests.exceptions.RequestException as exc:
            _logger.error('ElevenLabs network error: %s', exc)
            raise UserError(
                _('ElevenLabs network error: %s') % str(exc)
            ) from exc

    # ── Public API ───────────────────────────────────────
    def _trigger_outbound_call(
        self, agent_id, phone_number_id, to_number,
        dynamic_variables=None, config_override=None,
    ):
        """Trigger an outbound call via ElevenLabs Conversational AI + Twilio.

        Returns dict with at least ``conversation_id``.
        """
        payload = {
            'agent_id': agent_id,
            'agent_phone_number_id': phone_number_id,
            'to_number': to_number,
        }
        client_data = {}
        if dynamic_variables:
            client_data['dynamic_variables'] = dynamic_variables
        if config_override:
            client_data['conversation_config_override'] = config_override
        if client_data:
            payload['conversation_initiation_client_data'] = client_data

        _logger.info(
            'Triggering outbound call: agent=%s → %s',
            agent_id, to_number,
        )
        return self._make_request('POST', '/v1/convai/twilio/outbound-call', payload)

    def _get_conversation(self, conversation_id):
        """Fetch conversation details (transcript, status, analysis)."""
        return self._make_request(
            'GET', f'/v1/convai/conversations/{conversation_id}',
        )

    def _list_phone_numbers(self):
        """List phone numbers registered in ElevenLabs account."""
        return self._make_request('GET', '/v1/convai/phone-numbers')

    def _list_agents(self):
        """List conversational AI agents."""
        return self._make_request('GET', '/v1/convai/agents')
