import logging

from odoo import models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ConnectSettingsExt(models.Model):
    _inherit = 'connect.settings'

    def action_sync_elevenlabs(self):
        """Sync agents and phone numbers from ElevenLabs."""
        caller = self.env['dojo.elevenlabs.caller']
        synced_agents = 0
        synced_phones = 0

        # ── Sync agents ──────────────────────────────────
        try:
            agents_data = caller._list_agents()
        except UserError as exc:
            raise UserError(_('Failed to fetch agents: %s') % str(exc)) from exc

        Agent = self.env['dojo.elevenlabs.agent'].sudo()
        agents_list = agents_data.get('agents', []) if isinstance(agents_data, dict) else []
        for agent in agents_list:
            aid = agent.get('agent_id', '')
            if not aid:
                continue
            existing = Agent.search([('elevenlabs_id', '=', aid)], limit=1)
            vals = {
                'name': agent.get('name') or aid,
                'elevenlabs_id': aid,
            }
            if existing:
                existing.write(vals)
            else:
                Agent.create(vals)
            synced_agents += 1

        # ── Sync phone numbers ───────────────────────────
        try:
            phones_data = caller._list_phone_numbers()
        except UserError as exc:
            raise UserError(_('Failed to fetch phone numbers: %s') % str(exc)) from exc

        Phone = self.env['dojo.elevenlabs.phone'].sudo()
        # API may return a list directly or {"phone_numbers": [...]}
        if isinstance(phones_data, list):
            phones_list = phones_data
        elif isinstance(phones_data, dict):
            phones_list = phones_data.get('phone_numbers', phones_data.get('data', []))
        else:
            phones_list = []

        for phone in phones_list:
            pid = phone.get('phone_number_id', '')
            if not pid:
                continue
            existing = Phone.search([('elevenlabs_id', '=', pid)], limit=1)
            vals = {
                'elevenlabs_id': pid,
                'phone_number': phone.get('phone_number', ''),
                'provider': phone.get('provider', ''),
            }
            if existing:
                existing.write(vals)
            else:
                Phone.create(vals)
            synced_phones += 1

        _logger.info('ElevenLabs sync: %d agents, %d phones', synced_agents, synced_phones)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('ElevenLabs Sync Complete'),
                'message': _('Synced %d agents and %d phone numbers.') % (synced_agents, synced_phones),
                'type': 'success',
                'sticky': False,
            },
        }
