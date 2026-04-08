import ast
import logging
import time
import pytz
from datetime import time as dt_time

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AiCampaign(models.Model):
    _name = 'dojo.ai.campaign'
    _description = 'AI Call Campaign'
    _order = 'create_date desc'
    _inherit = ['mail.thread']

    # ── Core ─────────────────────────────────────────────
    name = fields.Char('Campaign Name', required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('paused', 'Paused'),
        ('done', 'Done'),
    ], default='draft', required=True, tracking=True)

    # ── ElevenLabs Config ────────────────────────────────
    elevenlabs_api_key = fields.Char(
        'ElevenLabs API Key',
        help='Override API key for this campaign. '
             'Leave blank to use key from Connect → Settings.',
    )
    elevenlabs_agent_id = fields.Many2one(
        'dojo.elevenlabs.agent',
        string='ElevenLabs Agent',
        help='Select a synced agent. Sync via Connect → Settings → API Keys.',
    )
    elevenlabs_phone_id = fields.Many2one(
        'dojo.elevenlabs.phone',
        string='ElevenLabs Phone Number',
        help='Select a synced phone number. Sync via Connect → Settings → API Keys.',
    )
    # Legacy char fields kept for backward compatibility
    agent_id = fields.Char(
        'Agent ID (manual)',
        help='Manual agent_id override. Used only if no synced agent is selected.',
    )
    phone_number_id = fields.Char(
        'Phone Number ID (manual)',
        help='Manual phone_number_id override. Used only if no synced phone is selected.',
    )
    from_number = fields.Char(
        'From Number',
        help='Display-only: the Twilio number making calls (e.g. +1234567890).',
    )
    first_message = fields.Text(
        'First Message',
        help='Agent opening line. Use {lead_name} for personalization.',
    )
    system_prompt_override = fields.Text(
        'System Prompt Override',
        help='Optional system prompt override sent to ElevenLabs per campaign.',
    )

    # ── Lead Targeting ───────────────────────────────────
    filter_domain = fields.Char(
        'Lead Filter', default='[]',
        help='Domain filter applied to crm.lead to select call targets.',
    )
    record_count = fields.Integer(
        'Matching Leads', compute='_compute_record_count', readonly=True,
    )
    tag_on_complete_id = fields.Many2one(
        'crm.tag', string='Tag After Call',
        help='Tag applied to lead after a successful AI call.',
    )
    skip_already_called = fields.Boolean(
        'Skip Already Called', default=True,
        help='Skip leads that already have a completed log in this campaign.',
    )

    # ── Scheduling ───────────────────────────────────────
    is_active = fields.Boolean('Cron Active', default=False)
    start_time = fields.Float('Start Time', default=9.0, help='Local start time (owner timezone).')
    end_time = fields.Float('End Time', default=17.0, help='Local end time (owner timezone).')
    delay_seconds = fields.Integer('Delay Between Calls (sec)', default=30)

    # ── Logs ─────────────────────────────────────────────
    log_ids = fields.One2many('dojo.ai.campaign.log', 'campaign_id', string='Call Logs', readonly=True)
    total_calls = fields.Integer(compute='_compute_stats', string='Total Calls')
    completed_calls = fields.Integer(compute='_compute_stats', string='Completed')
    failed_calls = fields.Integer(compute='_compute_stats', string='Failed')

    # ── Computes ─────────────────────────────────────────
    @api.depends('filter_domain')
    def _compute_record_count(self):
        Lead = self.env['crm.lead']
        for rec in self:
            try:
                domain = rec._parse_domain()
                rec.record_count = Lead.search_count(domain)
            except Exception:
                rec.record_count = 0

    @api.depends('log_ids', 'log_ids.status')
    def _compute_stats(self):
        for rec in self:
            logs = rec.log_ids
            rec.total_calls = len(logs)
            rec.completed_calls = len(logs.filtered(lambda l: l.status == 'completed'))
            rec.failed_calls = len(logs.filtered(lambda l: l.status == 'failed'))

    # ── Domain Helpers ───────────────────────────────────
    def _parse_domain(self):
        self.ensure_one()
        if not self.filter_domain:
            return []
        try:
            value = ast.literal_eval(self.filter_domain)
            if isinstance(value, (list, tuple)):
                return list(value)
            raise ValueError('Domain must be a list')
        except Exception as e:
            raise UserError(_('Invalid domain filter: %s') % e)

    # ── Time Window ──────────────────────────────────────
    @staticmethod
    def _float_to_time(value):
        if value is False or value is None:
            return None
        hours = max(0, min(23, int(value)))
        minutes = max(0, min(59, int(round((value - hours) * 60))))
        return dt_time(hours, minutes, 0)

    def _is_within_time_window(self):
        self.ensure_one()
        owner = self.create_uid or self.env.user
        tz_name = owner.tz or 'UTC'
        try:
            user_tz = pytz.timezone(tz_name)
        except pytz.UnknownTimeZoneError:
            user_tz = pytz.utc
        utc_now = pytz.utc.localize(fields.Datetime.now())
        local_now = utc_now.astimezone(user_tz).time()
        start_t = self._float_to_time(self.start_time) or dt_time(0, 0, 0)
        end_t = self._float_to_time(self.end_time) or dt_time(23, 59, 59)
        return start_t <= local_now <= end_t

    # ── Actions ──────────────────────────────────────────
    def action_start(self):
        for rec in self:
            rec.write({'state': 'running', 'is_active': True})

    def action_pause(self):
        for rec in self:
            rec.write({'state': 'paused', 'is_active': False})

    def action_done(self):
        for rec in self:
            rec.write({'state': 'done', 'is_active': False})

    def action_reset_draft(self):
        for rec in self:
            rec.write({'state': 'draft', 'is_active': False})

    def action_preview_leads(self):
        self.ensure_one()
        domain = self._parse_domain()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Matching Leads'),
            'res_model': 'crm.lead',
            'view_mode': 'list,form',
            'domain': domain,
            'target': 'current',
        }

    def action_view_logs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Call Logs'),
            'res_model': 'dojo.ai.campaign.log',
            'view_mode': 'list,form',
            'domain': [('campaign_id', '=', self.id)],
            'target': 'current',
        }

    def action_fetch_all_results(self):
        """Fetch results from ElevenLabs for all 'calling' logs in this campaign."""
        self.ensure_one()
        pending = self.log_ids.filtered(lambda l: l.status == 'calling' and l.elevenlabs_conversation_id)
        fetched = 0
        for log in pending:
            if log._fetch_conversation_results():
                fetched += 1
        # Tag leads that completed successfully
        for log in self.log_ids.filtered(lambda l: l.status == 'completed'):
            if self.tag_on_complete_id and log.lead_id:
                if self.tag_on_complete_id.id not in log.lead_id.tag_ids.ids:
                    log.lead_id.write({'tag_ids': [(4, self.tag_on_complete_id.id)]})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Results Fetched'),
                'message': _('Updated %d of %d pending calls.') % (fetched, len(pending)),
                'type': 'info',
                'sticky': False,
            },
        }

    def action_send_test_call(self):
        """Trigger a single test call to the first matching lead."""
        self.ensure_one()
        domain = self._parse_domain()
        lead = self.env['crm.lead'].search(domain, limit=1)
        if not lead:
            raise UserError(_('No leads match the current filter.'))
        phone = lead.phone or lead.mobile
        if not phone:
            raise UserError(_('Lead "%s" has no phone number.') % lead.name)
        self._call_lead(lead)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Test Call Initiated'),
                'message': _('Calling %s at %s') % (lead.name, phone),
                'type': 'success',
                'sticky': False,
            },
        }

    # ── Core Calling Logic ───────────────────────────────
    def _call_lead(self, lead):
        """Trigger a single outbound AI call for a lead."""
        self.ensure_one()
        phone = lead.phone or lead.mobile
        if not phone:
            _logger.warning('Campaign %s: Lead %s has no phone, skipping', self.name, lead.id)
            return False

        # Resolve ElevenLabs agent/phone IDs
        el_agent_id = (
            self.elevenlabs_agent_id.elevenlabs_id if self.elevenlabs_agent_id
            else self.agent_id
        )
        el_phone_id = (
            self.elevenlabs_phone_id.elevenlabs_id if self.elevenlabs_phone_id
            else self.phone_number_id
        )
        if not el_agent_id:
            raise UserError(_('No ElevenLabs agent configured for this campaign.'))
        if not el_phone_id:
            raise UserError(_('No ElevenLabs phone number configured for this campaign.'))

        Log = self.env['dojo.ai.campaign.log']
        log = Log.create({
            'campaign_id': self.id,
            'lead_id': lead.id,
            'phone': phone,
            'status': 'calling',
            'started_at': fields.Datetime.now(),
        })
        self.env.cr.commit()

        caller = self.env['dojo.elevenlabs.caller'].with_context(
            elevenlabs_api_key=self.elevenlabs_api_key or False,
        )

        # Build personalization
        lead_name = lead.contact_name or lead.partner_name or lead.name or ''
        dynamic_vars = {
            'lead_name': lead_name,
            'lead_email': lead.email_from or '',
            'lead_stage': lead.stage_id.name or '',
            'lead_source': lead.source_id.name if lead.source_id else '',
            'campaign_name': self.name,
        }

        config_override = {}
        if self.first_message:
            msg = self.first_message.replace('{lead_name}', lead_name)
            config_override['agent'] = {'first_message': msg}
        if self.system_prompt_override:
            prompt_text = self.system_prompt_override.replace('{lead_name}', lead_name)
            if 'agent' not in config_override:
                config_override['agent'] = {}
            config_override['agent']['prompt'] = {'prompt': prompt_text}

        try:
            result = caller._trigger_outbound_call(
                agent_id=el_agent_id,
                phone_number_id=el_phone_id,
                to_number=phone,
                dynamic_variables=dynamic_vars,
                config_override=config_override or None,
            )
            conv_id = result.get('conversation_id', '')
            log.write({
                'elevenlabs_conversation_id': conv_id,
                'status': 'calling',
            })

            # Post to lead chatter
            lead.message_post(
                body=_('AI Call initiated via campaign "%s". Conversation ID: %s') % (
                    self.name, conv_id or 'N/A'),
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )
            self.env.cr.commit()
            return log

        except Exception as e:
            _logger.exception('Campaign %s: call to lead %s failed', self.name, lead.id)
            log.write({
                'status': 'failed',
                'error_message': str(e)[:500],
                'ended_at': fields.Datetime.now(),
            })
            self.env.cr.commit()
            return log

    def _run_campaign(self):
        """Execute one pass of the campaign: call all pending leads."""
        self.ensure_one()
        if self.state != 'running':
            return

        domain = self._parse_domain()
        leads = self.env['crm.lead'].search(domain)

        if self.skip_already_called:
            called_lead_ids = self.log_ids.filtered(
                lambda l: l.status in ('completed', 'calling')
            ).mapped('lead_id').ids
            leads = leads.filtered(lambda l: l.id not in called_lead_ids)

        _logger.info('Campaign "%s": %d leads to call', self.name, len(leads))

        for lead in leads:
            # Re-check time window each iteration
            if not self._is_within_time_window():
                _logger.info('Campaign "%s": outside time window, stopping', self.name)
                break

            phone = lead.phone or lead.mobile
            if not phone:
                continue

            self._call_lead(lead)

            if self.delay_seconds and self.delay_seconds > 0:
                time.sleep(self.delay_seconds)

        # If all leads processed, mark done
        remaining = leads.filtered(lambda l: l.id not in self.log_ids.filtered(
            lambda lg: lg.status in ('completed', 'calling')
        ).mapped('lead_id').ids)
        if not remaining:
            self.write({'state': 'done', 'is_active': False})
            _logger.info('Campaign "%s": all leads called, marked done', self.name)

    # ── Cron Entry Point ─────────────────────────────────
    @api.model
    def _cron_run_ai_campaigns(self):
        """Cron: run all active campaigns within their time windows."""
        campaigns = self.search([('is_active', '=', True), ('state', '=', 'running')])
        for campaign in campaigns:
            if campaign._is_within_time_window():
                _logger.info('Cron: running campaign "%s"', campaign.name)
                try:
                    campaign._run_campaign()
                except Exception:
                    _logger.exception('Cron: campaign "%s" failed', campaign.name)
            else:
                _logger.info('Cron: skipping campaign "%s" (outside time window)', campaign.name)
