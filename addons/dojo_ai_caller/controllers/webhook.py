import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class AiCallerWebhook(http.Controller):

    def _json_response(self, data, status=200):
        return request.make_json_response(data, status=status)

    @http.route(
        '/dojo/ai-caller/post-call',
        type='http', auth='public', methods=['POST'], csrf=False,
    )
    def post_call_webhook(self, **kw):
        """Receive post-call data from ElevenLabs webhook.

        ElevenLabs can be configured to POST conversation results here.
        We use the conversation_id to match back to our log record
        and update transcript / outcome / duration.
        """
        try:
            data = json.loads(request.httprequest.data or '{}')
        except (json.JSONDecodeError, TypeError):
            data = kw
        conversation_id = data.get('conversation_id', '')
        if not conversation_id:
            return self._json_response(
                {'status': 'ignored', 'reason': 'no conversation_id'})

        Log = request.env['dojo.ai.campaign.log'].sudo()
        log = Log.search([
            ('elevenlabs_conversation_id', '=', conversation_id),
        ], limit=1)

        if not log:
            _logger.warning(
                'AI Caller webhook: no log for conversation %s', conversation_id,
            )
            return self._json_response(
                {'status': 'ignored', 'reason': 'unknown conversation_id'})

        vals = {}

        # Transcript
        transcript = data.get('transcript')
        if transcript:
            if isinstance(transcript, list):
                # ElevenLabs may send as list of {role, message} dicts
                vals['transcript'] = '\n'.join(
                    f"{t.get('role', '?')}: {t.get('message', '')}"
                    for t in transcript
                )
            elif isinstance(transcript, str):
                vals['transcript'] = transcript

        # Status mapping
        status = data.get('status', '')
        status_map = {
            'done': 'completed',
            'completed': 'completed',
            'failed': 'failed',
            'busy': 'no_answer',
            'no-answer': 'no_answer',
        }
        mapped = status_map.get(status)
        if mapped:
            vals['status'] = mapped

        # Call analysis / outcome
        analysis = data.get('analysis', {}) or {}
        outcome = analysis.get('call_successful')
        if outcome is True:
            vals['outcome'] = 'interested'
        elif outcome is False:
            vals['outcome'] = 'not_interested'

        custom_outcome = analysis.get('data', {}).get('outcome')
        if custom_outcome and custom_outcome in dict(
            Log._fields['outcome'].selection
        ):
            vals['outcome'] = custom_outcome

        # Duration
        duration = data.get('duration_seconds') or data.get('duration')
        if duration:
            try:
                vals['duration'] = int(float(duration))
            except (ValueError, TypeError):
                pass

        if vals:
            log.write(vals)
            _logger.info(
                'AI Caller webhook: updated log %s (conv %s) → %s',
                log.id, conversation_id, vals.get('status', 'update'),
            )

        return self._json_response({'status': 'ok', 'log_id': log.id})
