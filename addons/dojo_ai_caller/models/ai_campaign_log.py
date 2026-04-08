from odoo import models, fields, api, _
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class AiCampaignLog(models.Model):
    _name = 'dojo.ai.campaign.log'
    _description = 'AI Call Campaign Log'
    _order = 'id desc'

    campaign_id = fields.Many2one(
        'dojo.ai.campaign', string='Campaign',
        required=True, ondelete='cascade',
    )
    lead_id = fields.Many2one('crm.lead', string='Lead', ondelete='set null')
    phone = fields.Char('Phone')

    # ElevenLabs tracking
    elevenlabs_conversation_id = fields.Char('Conversation ID')

    status = fields.Selection([
        ('pending', 'Pending'),
        ('calling', 'Calling'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('no_answer', 'No Answer'),
    ], string='Status', default='pending', required=True)

    started_at = fields.Datetime('Started At')
    ended_at = fields.Datetime('Ended At')
    duration = fields.Integer('Duration (sec)', compute='_compute_duration', store=True)
    transcript = fields.Text('Transcript')
    outcome = fields.Selection([
        ('interested', 'Interested'),
        ('not_interested', 'Not Interested'),
        ('callback', 'Callback Requested'),
        ('voicemail', 'Voicemail'),
        ('no_answer', 'No Answer'),
        ('error', 'Error'),
    ], string='Outcome')
    error_message = fields.Text('Error')

    # Related fields for list display
    lead_name = fields.Char(related='lead_id.name', string='Lead Name', store=True)
    lead_stage = fields.Char(related='lead_id.stage_id.name', string='Stage')
    lead_tags = fields.Many2many(related='lead_id.tag_ids', string='Tags')

    @api.depends('started_at', 'ended_at')
    def _compute_duration(self):
        for rec in self:
            if rec.started_at and rec.ended_at:
                delta = rec.ended_at - rec.started_at
                rec.duration = int(delta.total_seconds())
            else:
                rec.duration = 0

    # ── Fetch results from ElevenLabs ────────────────────
    def _fetch_conversation_results(self):
        """Poll ElevenLabs GET /v1/convai/conversations/{id} and update this log.

        Returns True if the conversation is finished and results were written.
        """
        self.ensure_one()
        if not self.elevenlabs_conversation_id:
            return False

        caller = self.env['dojo.elevenlabs.caller'].with_context(
            elevenlabs_api_key=self.campaign_id.elevenlabs_api_key or False,
        )
        try:
            data = caller._get_conversation(self.elevenlabs_conversation_id)
        except Exception as e:
            _logger.warning('Fetch conv %s failed: %s', self.elevenlabs_conversation_id, e)
            return False

        conv_status = data.get('status', '')
        # ElevenLabs statuses: "processing", "done", "failed"
        if conv_status not in ('done', 'failed'):
            return False  # still in progress

        vals = {'ended_at': fields.Datetime.now()}

        # Status
        if conv_status == 'done':
            vals['status'] = 'completed'
        elif conv_status == 'failed':
            vals['status'] = 'failed'
            error = (data.get('metadata') or {}).get('error')
            if error:
                vals['error_message'] = str(error.get('message', error))[:500]

        # Duration
        metadata = data.get('metadata') or {}
        duration = metadata.get('call_duration_secs')
        if duration:
            vals['duration'] = int(duration)

        # Transcript — list of {role, message, ...} dicts
        transcript_items = data.get('transcript') or []
        if transcript_items:
            lines = []
            for item in transcript_items:
                role = item.get('role', '?')
                msg = item.get('message', '')
                lines.append(f'{role}: {msg}')
            vals['transcript'] = '\n'.join(lines)

        # Analysis / outcome
        analysis = data.get('analysis') or {}
        call_successful = analysis.get('call_successful', '')
        if call_successful == 'success':
            vals['outcome'] = 'interested'
        elif call_successful == 'failure':
            vals['outcome'] = 'not_interested'
        elif call_successful == 'unknown':
            vals['outcome'] = 'no_answer'

        # Check data collection results for a custom outcome
        data_results = analysis.get('data_collection_results') or {}
        custom_outcome = data_results.get('outcome', {}).get('value', '')
        valid_outcomes = dict(self._fields['outcome'].selection)
        if custom_outcome and custom_outcome in valid_outcomes:
            vals['outcome'] = custom_outcome

        self.write(vals)
        _logger.info(
            'Fetched results for conv %s → status=%s outcome=%s',
            self.elevenlabs_conversation_id,
            vals.get('status', ''),
            vals.get('outcome', ''),
        )
        return True

    def action_fetch_results(self):
        """Button: manually fetch results for this log entry."""
        self.ensure_one()
        if not self.elevenlabs_conversation_id:
            raise UserError(_('No conversation ID to fetch results for.'))
        if self._fetch_conversation_results():
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Results Updated'),
                    'message': _('Status: %s | Outcome: %s') % (
                        self.status, self.outcome or 'N/A'),
                    'type': 'success',
                    'sticky': False,
                },
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Call Still In Progress'),
                'message': _('The conversation has not finished yet. Try again later.'),
                'type': 'warning',
                'sticky': False,
            },
        }

    @api.model
    def _cron_fetch_call_results(self):
        """Cron: poll ElevenLabs for results of all 'calling' logs."""
        pending = self.search([
            ('status', '=', 'calling'),
            ('elevenlabs_conversation_id', '!=', False),
        ], limit=100)
        _logger.info('Cron fetch results: %d pending logs', len(pending))
        for log in pending:
            try:
                if log._fetch_conversation_results():
                    # Tag lead if campaign has tag_on_complete
                    campaign = log.campaign_id
                    if log.status == 'completed' and campaign.tag_on_complete_id and log.lead_id:
                        if campaign.tag_on_complete_id.id not in log.lead_id.tag_ids.ids:
                            log.lead_id.write({'tag_ids': [(4, campaign.tag_on_complete_id.id)]})
                    log.env.cr.commit()
            except Exception:
                _logger.exception('Cron: failed to fetch results for log %s', log.id)
