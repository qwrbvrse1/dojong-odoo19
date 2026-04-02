# -*- coding: utf-8 -*-

"""
Webhook endpoint for ElevenLabs post-conversation callbacks.

After an AI conversation ends, ElevenLabs sends a webhook with the full
transcript, analysis, and metadata. This controller processes that data
to create/update CRM leads and post transcripts to chatter.
"""

import json
import logging

from odoo import http
from odoo.http import request, Controller, route

_logger = logging.getLogger(__name__)


class AiWebhookController(Controller):

    @route(
        "/connect/ai/conversation_end",
        methods=["POST"],
        type="http",
        auth="public",
        csrf=False,
    )
    def conversation_end(self, **kw):
        """Process ElevenLabs post-conversation webhook.

        Expected payload:
        {
            "agent_id": "...",
            "conversation_id": "...",
            "call_sid": "...",       // passed as custom param during stream
            "caller_phone": "...",   // passed as custom param during stream
            "transcript": [
                {"role": "agent", "message": "Welcome to..."},
                {"role": "user", "message": "Hi, I want to..."},
                ...
            ],
            "analysis": {
                "summary": "Caller inquired about...",
                "sentiment": "positive",
                ...
            }
        }
        """
        try:
            raw_body = request.httprequest.get_data(as_text=True)
            data = json.loads(raw_body) if raw_body else {}
        except (json.JSONDecodeError, ValueError):
            _logger.warning("Invalid JSON in conversation_end webhook")
            return request.make_json_response(
                {"error": "Invalid JSON"}, status=400
            )

        agent_id_str = data.get("agent_id", "")
        if not agent_id_str:
            _logger.warning("conversation_end webhook missing agent_id")
            return request.make_json_response(
                {"error": "agent_id required"}, status=400
            )

        # Find the agent by ElevenLabs agent_id
        agent = request.env["connect.ai.agent"].sudo().search(
            [("elevenlabs_agent_id", "=", agent_id_str), ("active", "=", True)],
            limit=1,
        )
        if not agent:
            _logger.warning(
                "conversation_end: no agent found for elevenlabs_agent_id=%s",
                agent_id_str,
            )
            return request.make_json_response(
                {"error": "Agent not found"}, status=404
            )

        # Validate webhook signature if configured
        signature = request.httprequest.headers.get("X-ElevenLabs-Signature", "")
        if agent.webhook_secret and not agent.verify_webhook_signature(
            raw_body, signature
        ):
            _logger.warning("conversation_end: invalid webhook signature")
            return request.make_json_response(
                {"error": "Invalid signature"}, status=403
            )

        # Process using the webhook user context for proper permissions
        agent_with_user = agent.with_user(
            request.env.ref("connect.user_connect_webhook")
        )
        result = agent_with_user.process_conversation_end(data)
        return request.make_json_response(result)
