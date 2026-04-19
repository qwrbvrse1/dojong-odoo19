# -*- coding: utf-8 -*-
"""
API v1 endpoints for n8n orchestration.

Two-endpoint contract:
    POST /api/v1/ai/discover   — vector similarity → agent routing decision
    POST /api/v1/ai/execute    — agent-scoped intent execution

Auth: X-Api-Key header checked against ir.config_parameter
      ``ai_assistant.api_key``.  Set via Settings → AI Assistant.
"""

import hashlib
import hmac
import json
import logging
import time

from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


def _json_response(data, status=200):
    """Return a JSON HTTP response (n8n expects raw JSON, not JSON-RPC)."""
    body = json.dumps(data, default=str)
    return Response(
        body,
        status=status,
        content_type="application/json",
    )


class AiApiV1(http.Controller):
    """n8n-facing API for multi-agent AI orchestration."""

    # ── Auth helper ──────────────────────────────────────────────────────────

    @staticmethod
    def _verify_api_key():
        """
        Verify the X-Api-Key header against the stored secret.

        Returns:
            str | None: Error message if verification fails, None if OK.
        """
        api_key = request.httprequest.headers.get("X-Api-Key", "").strip()
        if not api_key:
            return "Missing X-Api-Key header"

        stored_key = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_str("ai_assistant.api_key", "")
        )
        if not stored_key:
            return "API key not configured on server"

        if not hmac.compare_digest(api_key, stored_key):
            return "Invalid API key"

        return None

    @staticmethod
    def _get_role(payload):
        """Extract and validate role from request payload."""
        role = payload.get("role", "instructor")
        if role not in ("admin", "instructor", "kiosk"):
            role = "instructor"
        return role

    # ── Discover ─────────────────────────────────────────────────────────────

    @http.route(
        "/api/v1/ai/discover",
        type="http",
        auth="public",
        methods=["POST", "OPTIONS"],
        csrf=False,
    )
    def discover(self, **kw):
        """
        Vector similarity → agent routing decision.

        Request:
            {
                "text": "check in Jordan",
                "role": "instructor"        // optional, default "instructor"
            }

        Response:
            {
                "agent": "attendance",
                "agent_name": "Attendance Agent",
                "intents": [
                    {"intent_type": "attendance_checkin", "score": 0.92},
                    ...
                ],
                "suggestions": ["Check in member", ...],
                "intent_count": 6,
                "system_prompt_available": true
            }
        """
        # CORS preflight
        if request.httprequest.method == "OPTIONS":
            return _json_response({})

        # Auth
        err = self._verify_api_key()
        if err:
            return _json_response({"error": err}, status=401)

        # Parse body
        try:
            payload = json.loads(request.httprequest.get_data(as_text=True))
        except (json.JSONDecodeError, TypeError):
            return _json_response({"error": "Invalid JSON body"}, status=400)

        text = (payload.get("text") or "").strip()
        if not text:
            return _json_response({"error": "Missing 'text' field"}, status=400)

        role = self._get_role(payload)

        # Run vector similarity
        try:
            ai_proc = request.env["ai.processor"].sudo()
            IntentSchema = request.env["ai.intent.schema"].sudo()
            intent_defs = IntentSchema.get_intent_definitions_for_llm(role)

            intent_defs, suggestions, identified_domain = ai_proc._apply_vector_filter(
                text, intent_defs, role
            )

            # Look up agent
            agent_name = None
            system_prompt_available = False
            if identified_domain and "ai.agent" in request.env:
                try:
                    agent_obj = (
                        request.env["ai.agent"]
                        .sudo()
                        .get_agent_for_domain(identified_domain)
                    )
                    if agent_obj:
                        agent_name = agent_obj.name
                        system_prompt_available = bool(agent_obj.system_prompt_template)
                except Exception:
                    pass

            # Build scored intents from vector matches
            scored_intents = []
            if suggestions:
                for s in suggestions:
                    scored_intents.append({
                        "intent_type": s.get("intent_type", ""),
                        "score": round(s.get("score", 0.0), 4),
                    })

            return _json_response({
                "agent": identified_domain,
                "agent_name": agent_name,
                "intents": scored_intents,
                "suggestions": [s.get("label") or s.get("intent_type") for s in (suggestions or [])],
                "intent_count": len(intent_defs),
                "system_prompt_available": system_prompt_available,
            })

        except Exception as e:
            _logger.error("Discover failed: %s", e, exc_info=True)
            return _json_response({"error": f"Discover failed: {e}"}, status=500)

    # ── Execute ──────────────────────────────────────────────────────────────

    @http.route(
        "/api/v1/ai/execute",
        type="http",
        auth="public",
        methods=["POST", "OPTIONS"],
        csrf=False,
    )
    def execute(self, **kw):
        """
        Agent-scoped intent execution.

        Supports two modes:
        1. **Full parse + execute** (text provided):
           The endpoint runs the full parse_and_confirm flow internally,
           auto-executing read-only intents and returning confirmation
           prompts for mutating ones.

        2. **Direct execute** (intent_type + resolved_data provided):
           Skips LLM parsing, executes the intent directly through
           the domain agent.

        Request (Mode 1 — parse):
            {
                "text": "check in Jordan",
                "role": "instructor",
                "agent": "attendance"       // optional hint
            }

        Request (Mode 2 — direct execute):
            {
                "intent_type": "attendance_checkin",
                "resolved_data": {"member_id": 42, "session_id": 15},
                "role": "instructor",
                "agent": "attendance"       // optional
            }

        Request (Mode 3 — confirm pending):
            {
                "session_key": "abc123",
                "confirmed": true
            }

        Response:
            Standard ai.assistant.service response dict.
        """
        if request.httprequest.method == "OPTIONS":
            return _json_response({})

        err = self._verify_api_key()
        if err:
            return _json_response({"error": err}, status=401)

        try:
            payload = json.loads(request.httprequest.get_data(as_text=True))
        except (json.JSONDecodeError, TypeError):
            return _json_response({"error": "Invalid JSON body"}, status=400)

        role = self._get_role(payload)
        service = request.env["ai.assistant.service"].sudo()

        # ── Mode 3: Confirm pending action ──────────────────────────────────
        session_key = payload.get("session_key")
        if session_key:
            confirmed = payload.get("confirmed", True)
            try:
                result = service.execute_confirmed(session_key, confirmed=confirmed)
                return _json_response(result)
            except Exception as e:
                _logger.error("Confirm execution failed: %s", e, exc_info=True)
                return _json_response({"error": f"Execution failed: {e}"}, status=500)

        # ── Mode 2: Direct execute (intent_type + resolved_data) ────────────
        intent_type = payload.get("intent_type")
        if intent_type:
            resolved_data = payload.get("resolved_data") or {}
            agent_domain = payload.get("agent")

            try:
                # Route through agent if specified
                if agent_domain and "ai.agent" in request.env:
                    agent_obj = (
                        request.env["ai.agent"]
                        .sudo()
                        .get_agent_for_domain(agent_domain)
                    )
                    if agent_obj:
                        result = agent_obj.execute(intent_type, resolved_data, role=role)
                        result["agent"] = agent_domain
                        result["agent_name"] = agent_obj.name
                        return _json_response(result)

                # Fallback: direct service execution (no action log for direct calls)
                result = service._execute_intent(
                    intent_type,
                    {},  # intent_data (raw LLM output) — not available in direct mode
                    resolved_data,
                    None,  # action_log — not available in direct mode
                )
                return _json_response(result)

            except Exception as e:
                _logger.error("Direct execution failed: %s", e, exc_info=True)
                return _json_response({"error": f"Execution failed: {e}"}, status=500)

        # ── Mode 1: Full parse + execute (text provided) ────────────────────
        text = (payload.get("text") or "").strip()
        if not text:
            return _json_response(
                {"error": "Provide 'text', 'intent_type', or 'session_key'"},
                status=400,
            )

        try:
            result = service.parse_and_confirm(text, role=role)
            return _json_response(result)
        except Exception as e:
            _logger.error("Parse+execute failed: %s", e, exc_info=True)
            return _json_response({"error": f"Parse failed: {e}"}, status=500)

    # ── Health Check ─────────────────────────────────────────────────────────

    @http.route(
        "/api/v1/ai/health",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def health(self, **kw):
        """
        Simple health check for n8n connection test.
        No auth required — returns minimal info.
        """
        vector_ok = False
        agent_count = 0
        try:
            if "ai.vector.store" in request.env:
                vector_ok = bool(
                    request.env["ai.vector.store"]
                    .sudo()
                    .search_count([])
                )
            if "ai.agent" in request.env:
                agent_count = (
                    request.env["ai.agent"]
                    .sudo()
                    .search_count([("active", "=", True)])
                )
        except Exception:
            pass

        return _json_response({
            "status": "ok",
            "version": "v1",
            "vector_store": vector_ok,
            "agent_count": agent_count,
        })
