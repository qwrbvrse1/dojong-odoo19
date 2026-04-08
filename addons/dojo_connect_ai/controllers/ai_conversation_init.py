# -*- coding: utf-8 -*-

"""
Conversation Initiation Webhook for ElevenLabs.

ElevenLabs fires this endpoint during Twilio's dialing period — before the
caller hears anything — so the agent can greet them by name and have full
context about their membership, belt rank, and last attendance.

ElevenLabs sends:
    POST /connect/ai/conversation_init
    Headers: X-Api-Key: <webhook_secret>
    Body: {
        "caller_id":      "+15551234567",
        "agent_id":       "elevenlabs-agent-id",
        "called_number":  "+18005551234",
        "call_sid":       "CA..."
    }

Odoo returns:
    {
        "type": "conversation_initiation_client_data",
        "dynamic_variables": {
            "caller_name":         "John Smith",
            "is_member":           "true",
            "membership_status":   "Active",
            "belt_rank":           "Blue Belt",
            "total_classes":       "47",
            "last_class_date":     "April 5, 2026",
            "days_since_class":    "3",
            "program":             "Brazilian Jiu-Jitsu"
        },
        "conversation_config_override": {
            "agent": {
                "first_message": "Hi John! Great to hear from you. How can I help?"
            }
        }
    }

Configure in ElevenLabs:
  1. Settings → Conversation Initiation Webhook → URL = <odoo_url>/connect/ai/conversation_init
     Add header: X-Api-Key = <agent's Tool API Key>
  2. Agent → Security tab → enable "Fetch conversation initiation data for inbound Twilio calls"
  3. Define these dynamic variables on the agent: caller_name, is_member,
     membership_status, belt_rank, total_classes, last_class_date,
     days_since_class, program
"""

import json
import logging

from odoo import http
from odoo.http import request, Controller, route

_logger = logging.getLogger(__name__)


class AiConversationInitController(Controller):

    @route(
        "/connect/ai/conversation_init",
        methods=["POST"],
        type="http",
        auth="public",
        csrf=False,
    )
    def conversation_init(self, **kw):
        """Return conversation initiation data for ElevenLabs.

        Authenticates via X-Api-Key matching the agent's webhook_secret.
        Looks up the caller by phone number and returns dynamic variables.
        """
        # ── Authentication ──────────────────────────────────────────
        token = request.httprequest.headers.get("X-Api-Key", "")
        if not token:
            _logger.warning("conversation_init: missing X-Api-Key header")
            return request.make_json_response({"error": "Unauthorized"}, status=401)

        agent = request.env["connect.ai.agent"].sudo().search(
            [("webhook_secret", "=", token), ("active", "=", True)], limit=1
        )
        if not agent:
            _logger.warning("conversation_init: no agent found for provided token")
            return request.make_json_response({"error": "Unauthorized"}, status=401)

        # ── Parse request body ───────────────────────────────────────
        try:
            raw = request.httprequest.get_data(as_text=True)
            data = json.loads(raw) if raw else {}
        except (json.JSONDecodeError, ValueError):
            data = kw

        caller_id = data.get("caller_id", "")
        call_sid = data.get("call_sid", "")

        _logger.info(
            "conversation_init: agent=%s caller=%s call_sid=%s",
            agent.name, caller_id, call_sid,
        )

        # ── Build initiation data via agent model ────────────────────
        result = agent.sudo().get_conversation_init_data(
            caller_phone=caller_id,
            call_sid=call_sid,
        )
        return request.make_json_response(result)
