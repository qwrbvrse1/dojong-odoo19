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
        include_prompt = payload.get("include_prompt", False)

        # Run vector similarity
        try:
            ai_proc = request.env["ai.processor"].sudo()
            IntentSchema = request.env["ai.intent.schema"].sudo()
            intent_defs = IntentSchema.get_intent_definitions_for_llm(role)

            intent_defs, suggestions, identified_domain = ai_proc._apply_vector_filter(
                text, intent_defs, role
            )

            # Look up agent
            agent_obj = None
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
            # Note: vector suggestions use 'similarity' key not 'score'
            scored_intents = []
            if suggestions:
                for s in suggestions:
                    score = s.get("similarity") or s.get("score") or 0.0
                    scored_intents.append({
                        "intent_type": s.get("intent_type", ""),
                        "score": round(score, 4),
                    })

            result = {
                "agent": identified_domain,
                "agent_name": agent_name,
                "intents": scored_intents,
                "suggestions": [s.get("label") or s.get("intent_type") for s in (suggestions or [])],
                "intent_count": len(intent_defs),
                "system_prompt_available": system_prompt_available,
            }

            # When include_prompt=true, return the full system prompt and
            # intent definitions so n8n can use them in its own LLM call.
            if include_prompt:
                service = request.env["ai.assistant.service"].sudo()
                db_ctx = service._build_db_context(text)
                intent_defs_str = ai_proc._format_intent_definitions(intent_defs)

                if agent_obj and agent_obj.system_prompt_template:
                    try:
                        system_prompt = agent_obj.system_prompt_template.format(
                            intent_definitions=intent_defs_str,
                            db_context=db_ctx or "No specific context available.",
                            user_input=text,
                        )
                    except Exception:
                        system_prompt = None
                else:
                    system_prompt = None

                result["system_prompt"] = system_prompt
                result["intent_definitions"] = intent_defs
                result["db_context"] = db_ctx

            return _json_response(result)

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

        # ── Mode 4: Compound chain (multiple intents) ───────────────────────
        #
        # Used by n8n when the LLM identifies multiple sequential actions.
        # Validates the chain and returns a confirmation prompt + session_key.
        # The caller then confirms via Mode 3 (session_key + confirmed=true).
        #
        # Request body:
        #   {
        #     "intents": [
        #       {"intent_type": "attendance_checkin", "parameters": {"member_name": "Jordan"}, "confidence": 0.95},
        #       {"intent_type": "schedule_today", "parameters": {}, "confidence": 0.9}
        #     ],
        #     "role": "instructor"
        #   }
        intents = payload.get("intents")
        if intents and isinstance(intents, list) and len(intents) > 0:
            try:
                compound_data = {"intents": intents}
                result = service.handle_compound_command(compound_data, role=role)
                return _json_response(result)
            except Exception as e:
                _logger.error("Compound execution failed: %s", e, exc_info=True)
                return _json_response({"error": f"Compound failed: {e}"}, status=500)

        # ── Mode 2: Direct execute (intent_type + parameters) ─────────────
        #
        # Used by n8n after it has called /discover and parsed the intent
        # via its own LLM node.  Accepts raw LLM output (parameters with
        # names, not IDs) and runs entity resolution, validation, audit
        # logging, and the confirmation flow — matching parse_and_confirm().
        #
        # Request body:
        #   {
        #     "intent_type": "attendance_checkin",
        #     "parameters": {"member_name": "Jordan", "date": "today"},
        #     "confidence": 0.95,
        #     "agent": "attendance",
        #     "role": "instructor"
        #   }
        intent_type = payload.get("intent_type")
        if intent_type:
            # Normalise aliases so the log and handler always use canonical names
            _ALIASES = {
                # CRM lead
                "create_lead": "lead_create", "create_lead_confirm": "lead_create",
                "crm_lead_create": "lead_create",
                "lead_delete": "lead_mark_lost", "delete_lead": "lead_mark_lost",
                "crm_lead_delete": "lead_mark_lost",
                "qualify_lead": "lead_qualify", "convert_lead": "lead_convert",
                "mark_lead_won": "lead_mark_won", "mark_lead_lost": "lead_mark_lost",
                "lead_list": "lead_lookup", "list_leads": "lead_lookup",
                # Attendance
                "checkin": "attendance_checkin", "check_in": "attendance_checkin",
                "checkout": "attendance_checkout", "check_out": "attendance_checkout",
                # Classes
                "create_class": "class_create", "schedule_class": "class_create",
                "cancel_class": "class_cancel",
                # Members
                "promote_belt": "belt_promote", "enroll_member": "member_enroll",
                "unenroll_member": "member_unenroll", "create_member": "member_create",
                # Tasks
                "list_tasks": "task_list",
            }
            intent_type = _ALIASES.get(intent_type, intent_type)
            parameters = payload.get("parameters") or payload.get("resolved_data") or {}
            # n8n's $fromAI() may serialize parameters as a JSON string — parse it
            if isinstance(parameters, str):
                try:
                    parameters = json.loads(parameters)
                except (json.JSONDecodeError, TypeError):
                    parameters = {}
            confidence = float(payload.get("confidence", 0.0))
            # chat_session_id forwarded from n8n (added as Execute_Intent body field)
            chat_session_id = payload.get("session_id") or payload.get("chat_session_id") or None

            try:
                import time as _time
                start = _time.time()

                # Build intent_data dict matching LLM parse output format
                intent_data = {
                    "intent_type": intent_type,
                    "parameters": parameters,
                    "confidence": confidence,
                }

                # Entity resolution (names → DB IDs)
                resolved_data = service._resolve_entities(intent_data)

                # Pre-execution validation (ambiguous names, missing params)
                validation = service._validate_before_execute(
                    intent_type, intent_data, resolved_data,
                )
                if not validation.get("valid", True):
                    return _json_response({
                        "success": True,
                        "state": "needs_clarification",
                        "intent": intent_data,
                        "resolved_data": resolved_data,
                        "response": validation["clarification"],
                        "auto_executed": False,
                        "result": None,
                        "error": None,
                    })

                # Audit log
                ActionLog = request.env["ai.action.log"].sudo()
                requires_confirmation = service._requires_confirmation(intent_type)
                log = ActionLog.log_parse(
                    input_text=f"[n8n] {intent_type}",
                    role=role,
                    intent_type=intent_type,
                    parsed_intent=intent_data,
                    confidence=round(confidence * 100, 1),
                    resolved_data=resolved_data,
                    confirmation_prompt=None,
                    requires_confirmation=requires_confirmation,
                    input_type="text",
                    audio_attachment_id=None,
                )

                # Read-only → auto-execute; mutating → confirmation flow
                if not requires_confirmation:
                    exec_result = service._execute_intent(
                        intent_type, intent_data, resolved_data, log,
                    )
                    elapsed = int((_time.time() - start) * 1000)
                    log.log_execution(
                        success=exec_result.get("success", False),
                        result=exec_result,
                        execution_time_ms=elapsed,
                        is_undoable=False,
                    )
                    formatted = service._format_exec_result_as_response(
                        intent_type, exec_result,
                    )
                    return _json_response({
                        "success": True,
                        "state": "executed",
                        "session_key": log.session_key,
                        "intent": intent_data,
                        "auto_executed": True,
                        "result": exec_result,
                        "response": formatted or "",
                        "resolved_data": resolved_data,
                        "error": None,
                    })

                # Mutating intent → return confirmation prompt + session_key
                confirmation_prompt = service._build_confirmation_prompt(
                    intent_type, intent_data, resolved_data,
                )
                log.write({"confirmation_prompt": confirmation_prompt})

                # Cache session_key by chat_session_id so handle_command can
                # intercept "yes/no" on the next message without n8n losing it
                if chat_session_id and log.session_key:
                    import time as _time2
                    svc_cls = type(service)
                    svc_cls._pending_confirm_cache[chat_session_id] = (
                        log.session_key,
                        _time2.time() + svc_cls._PENDING_CONFIRM_TTL,
                    )
                    _logger.info(
                        "Cached pending confirmation session_key=%s for chat_session_id=%s",
                        log.session_key, chat_session_id,
                    )

                return _json_response({
                    "success": True,
                    "state": "pending_confirmation",
                    "session_key": log.session_key,
                    "intent": intent_data,
                    "confirmation_prompt": confirmation_prompt,
                    "resolved_data": resolved_data,
                    "auto_executed": False,
                    "result": None,
                    "response": confirmation_prompt,
                    "tool_hint": "Call Confirm_Intent with confirmed=true (Yes) or confirmed=false (No)",
                    "error": None,
                })

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

    # ── Confirm (session_key-free confirmation) ───────────────────────────────

    @http.route(
        "/api/v1/ai/confirm",
        type="http",
        auth="public",
        methods=["POST", "OPTIONS"],
        csrf=False,
    )
    def confirm(self, **kw):
        """
        Confirm or cancel the most recent pending action without needing session_key.

        n8n's AI Agent uses this when the user says yes/no after a
        pending_confirmation — the LLM doesn't have to remember session_key.

        Request:
            {
                "confirmed": true,   // true = yes/confirm, false = no/cancel
                "role": "instructor" // optional
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

        # confirmed defaults to True; also accept "yes"/"no" strings from $fromAI()
        confirmed_raw = payload.get("confirmed")
        if confirmed_raw is None:
            confirmed = True
        elif isinstance(confirmed_raw, bool):
            confirmed = confirmed_raw
        else:
            confirmed = str(confirmed_raw).lower().strip() not in ("false", "no", "0", "cancel", "n")

        session_key = None

        # Strategy 1: session_id → in-memory cache (fastest, no DB)
        session_id = payload.get("session_id") or payload.get("chat_session_id")
        if session_id:
            import time as _time_mod
            svc_cls = type(request.env["ai.assistant.service"].sudo())
            cached = svc_cls._pending_confirm_cache.get(session_id)
            if cached:
                s_key, expires_at = cached
                if _time_mod.time() < expires_at:
                    session_key = s_key
                    del svc_cls._pending_confirm_cache[session_id]
                    _logger.info(
                        "Confirm endpoint: found session_key=%s via cache (session_id=%s)",
                        session_key, session_id,
                    )
                else:
                    del svc_cls._pending_confirm_cache[session_id]

        # Strategy 2: DB fallback — most recent pending log within 10 minutes
        if not session_key:
            import datetime as _dt
            cutoff = _dt.datetime.utcnow() - _dt.timedelta(minutes=10)
            ActionLog = request.env["ai.action.log"].sudo()
            pending_log = ActionLog.search([
                ("requires_confirmation", "=", True),
                ("confirmation_status", "=", "pending"),
                ("session_key", "!=", False),
                ("create_date", ">=", cutoff.strftime("%Y-%m-%d %H:%M:%S")),
            ], order="create_date desc", limit=1)
            if pending_log:
                session_key = pending_log.session_key
                _logger.info(
                    "Confirm endpoint: found session_key=%s via DB fallback",
                    session_key,
                )

        if not session_key:
            return _json_response({
                "success": False,
                "state": "no_pending",
                "response": "No pending action found to confirm. Please make your request again.",
                "error": "no_pending_action",
            })
        _logger.info(
            "Confirm endpoint: %s session_key=%s",
            "confirming" if confirmed else "cancelling",
            session_key,
        )

        try:
            service = request.env["ai.assistant.service"].sudo()
            result = service.execute_confirmed(session_key, confirmed=confirmed)
            return _json_response(result)
        except Exception as e:
            _logger.error("Confirm endpoint failed: %s", e, exc_info=True)
            return _json_response({"error": f"Execution failed: {e}"}, status=500)

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

    # ── Tools (OpenAI function-calling format) ───────────────────────────────

    @http.route(
        "/api/v1/ai/tools",
        type="http",
        auth="public",
        methods=["GET", "POST", "OPTIONS"],
        csrf=False,
    )
    def tools(self, **kw):
        """
        Return intent definitions as OpenAI function-calling tool definitions.

        n8n's AI Agent node can load these directly to give the LLM
        access to all Odoo intents as callable tools.

        Query params / JSON body:
            role (str): Filter tools by role (default: "instructor")

        Response:
            {
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "attendance_checkin",
                            "description": "Check in a member...",
                            "parameters": { ... JSON Schema ... }
                        }
                    },
                    ...
                ],
                "execute_url": "/api/v1/ai/execute",
                "tool_count": 42
            }
        """
        if request.httprequest.method == "OPTIONS":
            return _json_response({})

        err = self._verify_api_key()
        if err:
            return _json_response({"error": err}, status=401)

        # Accept role from query string (GET) or JSON body (POST)
        role = "instructor"
        if request.httprequest.method == "POST":
            try:
                payload = json.loads(
                    request.httprequest.get_data(as_text=True) or "{}"
                )
                role = self._get_role(payload)
            except (json.JSONDecodeError, TypeError):
                pass
        else:
            role = request.params.get("role", "instructor")
            if role not in ("admin", "instructor", "kiosk"):
                role = "instructor"

        try:
            IntentSchema = request.env["ai.intent.schema"].sudo()
            schemas = IntentSchema.search(
                [("active", "=", True)], order="sequence, intent_type"
            )

            tools = []
            for schema in schemas:
                if not schema.check_role_permission(role):
                    continue

                # Build description
                desc_parts = []
                if schema.description:
                    desc_parts.append(schema.description.strip())
                examples = schema.get_example_phrases_list()
                if examples:
                    desc_parts.append(
                        "Examples: " + "; ".join(examples[:5])
                    )
                description = "\n".join(desc_parts) if desc_parts else schema.name

                # Build parameters JSON Schema
                params = schema.get_parameters_schema_dict()
                if params and "type" in params and "properties" in params:
                    parameters_schema = params
                elif params:
                    properties = {}
                    required = []
                    for key, value in params.items():
                        if isinstance(value, str):
                            properties[key] = {
                                "type": "string",
                                "description": value,
                            }
                        elif isinstance(value, dict):
                            prop = {
                                "type": value.get("type", "string"),
                                "description": value.get("description", key),
                            }
                            if value.get("enum"):
                                prop["enum"] = value["enum"]
                            properties[key] = prop
                            if value.get("required"):
                                required.append(key)
                    parameters_schema = {
                        "type": "object",
                        "properties": properties,
                    }
                    if required:
                        parameters_schema["required"] = required
                else:
                    parameters_schema = {
                        "type": "object",
                        "properties": {},
                    }

                tools.append({
                    "type": "function",
                    "function": {
                        "name": schema.intent_type,
                        "description": description,
                        "parameters": parameters_schema,
                    },
                })

            return _json_response({
                "tools": tools,
                "execute_url": "/api/v1/ai/execute",
                "tool_count": len(tools),
            })

        except Exception as e:
            _logger.error("Tools endpoint failed: %s", e, exc_info=True)
            return _json_response(
                {"error": f"Failed to generate tools: {e}"}, status=500
            )
