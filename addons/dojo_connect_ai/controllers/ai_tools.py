# -*- coding: utf-8 -*-

"""
Single tool endpoint called by the ElevenLabs AI agent (Kai) during live calls.

The ElevenLabs agent sends the caller's natural-language request here and
gets back a text response. Odoo routes it through the ai_assistant AI
intent engine, which handles 57+ intents (schedule lookups, member queries,
trial bookings, enrollment, etc.).

Authentication: X-Api-Key header matching the agent's webhook_secret.
"""

import json
import logging

from odoo import http
from odoo.http import request, Controller, route

_logger = logging.getLogger(__name__)


class AiToolsController(Controller):

    # ------------------------------------------------------------------
    # Single unified tool — routes everything through ai_assistant
    # ------------------------------------------------------------------

    @route(
        "/connect/ai/tool/ask",
        methods=["POST"],
        type="http",
        auth="public",
        csrf=False,
    )
    def tool_ask(self, **kw):
        """Handle any caller request via the ai_assistant AI engine.

        Auth: X-Api-Key header must match an AI agent's webhook_secret.

        ElevenLabs sends:
            {
                "user_message": "What classes are available today?",
                "caller_phone": "+15551234567",   // optional
                "call_sid": "CA..."               // optional, for transfers
            }

        Returns:
            {"response": "Here are today's classes: ..."}
        """
        token = request.httprequest.headers.get("X-Api-Key", "")
        if not token:
            return request.make_json_response(
                {"error": "Unauthorized"}, status=401
            )

        # Authenticate via global Connect settings key
        settings = request.env["connect.settings"].sudo()
        expected_key = settings.get_param("elevenlabs_tool_api_key")
        if not expected_key or token != expected_key:
            return request.make_json_response(
                {"error": "Unauthorized"}, status=401
            )

        try:
            data = json.loads(request.httprequest.get_data(as_text=True) or "{}")
        except (json.JSONDecodeError, ValueError):
            data = kw

        user_message = data.get("user_message", "").strip()
        if not user_message:
            return request.make_json_response(
                {"error": "user_message is required"}, status=400
            )

        # Identify agent from payload agent_id or fall back to first active
        agent = False
        el_agent_id = data.get("agent_id", "")
        if el_agent_id:
            agent = request.env["connect.ai.agent"].sudo().search(
                [("elevenlabs_agent_id", "=", el_agent_id), ("active", "=", True)], limit=1
            )
        if not agent:
            agent = request.env["connect.ai.agent"].sudo().search(
                [("active", "=", True)], limit=1
            )

        tools = request.env["connect.ai.tools"].with_user(
            request.env.ref("connect.user_connect_webhook")
        )
        result = tools.ask_assistant(
            user_message=user_message,
            caller_phone=data.get("caller_phone", ""),
            call_sid=data.get("call_sid", ""),
            agent_id=agent.id,
        )
        return request.make_json_response(result)
