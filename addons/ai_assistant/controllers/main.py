# -*- coding: utf-8 -*-
"""
HTTP / JSON-RPC endpoints for the Dojo AI Assistant.

This controller provides a reusable API that can be consumed by:
- Instructor Dashboard voice assistant component
- Kiosk application
- Other frontend applications

Routes
------
POST /dojo/ai/text          (type=jsonrpc)  – text query → parse + auto-execute or confirmation
POST /dojo/ai/voice         (type=http)    – multipart audio upload → STT → parse + confirm
POST /dojo/ai/confirm       (type=jsonrpc) – confirm or reject pending action
POST /dojo/ai/undo          (type=jsonrpc) – undo last undoable action
POST /dojo/ai/send_message  (type=jsonrpc) – send confirmed parent message (legacy)
GET  /dojo/ai/history       (type=jsonrpc) – get recent AI action history
GET  /dojo/ai/intents       (type=jsonrpc) – get available intent schemas
"""

import json
import logging
import base64
import os
import hashlib
from datetime import datetime as _dt

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class AiAssistantController(http.Controller):

    # ═══════════════════════════════════════════════════════════════════════════
    # New Two-Phase Confirmation API
    # ═══════════════════════════════════════════════════════════════════════════

    @http.route("/dojo/ai/text", type="jsonrpc", auth="user", methods=["POST"])
    def text_query(self, text="", role=None, conversation_history=None, **kwargs):
        """
        Process a plain-text query through the dojo AI assistant.
        
        Uses the new two-phase confirmation flow:
        - Read-only queries auto-execute and return results
        - Mutating queries return a confirmation prompt and session_key
        
        Args:
            text: Natural language query
            role: Optional role override (kiosk/instructor/admin)
            conversation_history: Optional list of {role, text} dicts for context chaining
        
        Returns:
            {
                success: bool,
                state: "pending_confirmation" | "executed" | "error",
                session_key: str (for confirmation),
                intent: dict | None,
                confirmation_prompt: str | None,
                resolved_data: dict | None,
                auto_executed: bool,
                result: dict | None,
                response: str | None,
                error: str | None
            }
        """
        text = (text or "").strip()
        if not text:
            return {"success": False, "state": "error", "error": "No text provided."}

        # Determine role from user groups if not specified
        if not role:
            role = self._get_user_role()

        # Decode conversation_history if sent as a JSON string
        if isinstance(conversation_history, str):
            try:
                conversation_history = json.loads(conversation_history)
            except Exception:
                conversation_history = None

        try:
            assistant = request.env["ai.assistant.service"]
            result = assistant.handle_command(text, role=role, input_type="text", conversation_history=conversation_history)

            # Surface vector routing suggestions at response top-level for UI
            intent = result.get("intent") or {}
            if isinstance(intent, dict) and intent.get("vector_suggestions"):
                result["suggestions"] = intent.pop("vector_suggestions")

            return result
        except Exception as exc:
            _logger.error("Dojo AI /dojo/ai/text failed: %s", exc, exc_info=True)
            return {"success": False, "state": "error", "error": str(exc)}

    @http.route("/dojo/ai/confirm", type="jsonrpc", auth="user", methods=["POST"])
    def confirm_action(self, session_key="", confirmed=True, **kwargs):
        """
        Confirm or reject a pending action from parse_and_confirm.
        
        Args:
            session_key: Session key from the parse_and_confirm response
            confirmed: True to execute, False to reject
        
        Returns:
            {
                success: bool,
                state: "executed" | "rejected" | "error",
                result: dict | None,
                undo_available: bool,
                undo_expires_in_minutes: int | None,
                error: str | None
            }
        """
        if not session_key:
            return {"success": False, "state": "error", "error": "No session_key provided."}

        try:
            assistant = request.env["ai.assistant.service"]
            result = assistant.execute_confirmed(session_key, confirmed=bool(confirmed))
            return result
        except Exception as exc:
            _logger.error("Dojo AI /dojo/ai/confirm failed: %s", exc, exc_info=True)
            return {"success": False, "state": "error", "error": str(exc)}

    @http.route("/dojo/ai/undo", type="jsonrpc", auth="user", methods=["POST"])
    def undo_action(self, **kwargs):
        """
        Initiate undo of the most recent undoable action.
        
        Returns a confirmation prompt for the undo operation.
        Use /dojo/ai/confirm to execute or cancel the undo.
        
        Returns:
            {
                success: bool,
                state: "pending_confirmation" | "error",
                session_key: str | None,
                confirmation_prompt: str | None,
                undo_target: dict | None,
                error: str | None
            }
        """
        try:
            assistant = request.env["ai.assistant.service"]
            result = assistant.undo_last_action(user_id=request.env.user.id)
            return result
        except Exception as exc:
            _logger.error("Dojo AI /dojo/ai/undo failed: %s", exc, exc_info=True)
            return {"success": False, "state": "error", "error": str(exc)}

    # ═══════════════════════════════════════════════════════════════════════════
    # Voice Input (STT → Text → AI)
    # ═══════════════════════════════════════════════════════════════════════════

    @http.route("/dojo/ai/voice", type="http", auth="user", methods=["POST"], csrf=False)
    def voice_query(self, role=None, **kwargs):
        """
        Accept a multipart audio file, transcribe it with ElevenLabs STT, then
        process through the dojo AI assistant with confirmation flow.

        Returns JSON: {
            success: bool,
            transcribed: str,
            state: str,
            session_key: str | None,
            intent: dict | None,
            confirmation_prompt: str | None,
            resolved_data: dict | None,
            auto_executed: bool,
            result: dict | None,
            response: str | None,
            error: str | None
        }
        """
        def _json_resp(data, status=200):
            return request.make_response(
                json.dumps(data, ensure_ascii=False).encode("utf-8"),
                headers=[("Content-Type", "application/json; charset=utf-8")],
                status=status,
            )

        try:
            audio_file = request.httprequest.files.get("audio")
            if not audio_file:
                return _json_resp({"success": False, "state": "error", "error": "No audio file provided."}, 400)

            audio_bytes = audio_file.read()
            if not audio_bytes:
                return _json_resp({"success": False, "state": "error", "error": "Empty audio file."}, 400)

            # Store audio as attachment for audit trail
            attachment = None
            try:
                attachment = request.env["ir.attachment"].sudo().create({
                    "name": f"voice_input_{audio_file.filename or 'audio.webm'}",
                    "datas": base64.b64encode(audio_bytes),
                    "mimetype": audio_file.content_type or "audio/webm",
                    "res_model": "ai.action.log",
                })
            except Exception as e:
                _logger.warning("Could not save audio attachment: %s", e)

            # Step 1: Speech-to-text via ElevenLabs
            # Use the logged-in user's language when a walkie station is active
            walkie_id_raw = kwargs.get("walkie_id")
            if walkie_id_raw:
                from odoo.addons.ai_assistant.models.dojo_walkie_talkie import _odoo_lang_to_stt
                lang = _odoo_lang_to_stt(request.env.user.lang)
            else:
                lang = request.env["ir.config_parameter"].sudo().get_str(
                    "elevenlabs_connector.language", "en"
                )
            try:
                transcribed = request.env["elevenlabs.service"].transcribe_audio(
                    audio_bytes, language=lang
                )
            except Exception as exc:
                _logger.error("Dojo AI STT failed: %s", exc)
                return _json_resp(
                    {"success": False, "state": "error", "error": "Speech-to-text failed. Please configure the ElevenLabs API key in Settings → ElevenLabs Voice Connector."},
                )

            transcribed = (transcribed or "").strip()
            if not transcribed:
                return _json_resp(
                    {"success": False, "state": "error", "error": "Could not understand the audio. Please try again."}
                )

            # Determine role
            if not role:
                role = self._get_user_role()

            # Extract optional conversation history for context chaining
            conversation_history = None
            history_raw = kwargs.get("conversation_history")
            if history_raw:
                try:
                    conversation_history = json.loads(history_raw)
                except Exception:
                    pass

            # Step 2: Process through dojo AI assistant with confirmation flow
            assistant = request.env["ai.assistant.service"]
            result = assistant.handle_command(
                transcribed,
                role=role,
                input_type="voice",
                audio_attachment_id=attachment.id if attachment else None,
                conversation_history=conversation_history,
            )

            result["transcribed"] = transcribed

            # ── Post to Discuss (Elder / Channel Beta modes) ──────────────
            walkie_id = kwargs.get("walkie_id")
            channel = kwargs.get("channel")
            if walkie_id:
                try:
                    walkie_id = int(walkie_id)
                    walkie_rec = request.env["ai.walkie.talkie"].sudo().browse(walkie_id).exists()
                    if walkie_rec and walkie_rec.mode in ("elder_beta", "channel_beta"):
                        from odoo.addons.ai_assistant.models.dojo_walkie_talkie import _odoo_lang_to_stt
                        source_lang = _odoo_lang_to_stt(request.env.user.lang)
                        author_id = request.env.user.partner_id.id
                        walkie_rec.post_voice_to_discuss(
                            audio_bytes, transcribed,
                            channel_type=channel, author_id=author_id,
                            source_lang=source_lang,
                        )
                        ai_text = result.get("response") or result.get("confirmation_prompt") or ""
                        if ai_text:
                            walkie_rec.post_ai_response_to_discuss(
                                ai_text, channel_type=channel,
                                source_lang=source_lang,
                            )
                except Exception:
                    _logger.warning("Discuss posting failed (walkie_id=%s)", walkie_id, exc_info=True)

            return _json_resp(result)

        except Exception as exc:
            _logger.error("Dojo AI /dojo/ai/voice failed: %s", exc, exc_info=True)
            return _json_resp({"success": False, "state": "error", "error": str(exc)}, 500)

    # ═══════════════════════════════════════════════════════════════════════════
    # Admin / Monitoring Endpoints
    # ═══════════════════════════════════════════════════════════════════════════

    @http.route("/dojo/ai/history", type="jsonrpc", auth="user", methods=["GET", "POST"])
    def get_history(self, limit=20, offset=0, user_only=True, **kwargs):
        """
        Get recent AI action history.
        
        Args:
            limit: Maximum records to return (default 20, max 100)
            offset: Pagination offset
            user_only: If True, show only current user's actions
        
        Returns:
            {
                success: bool,
                records: list[dict],
                total: int,
                error: str | None
            }
        """
        try:
            ActionLog = request.env["ai.action.log"]

            domain = []
            if user_only:
                domain.append(("user_id", "=", request.env.user.id))

            limit = min(int(limit or 20), 100)
            offset = int(offset or 0)

            total = ActionLog.search_count(domain)
            logs = ActionLog.search(
                domain,
                order="timestamp desc",
                limit=limit,
                offset=offset,
            )

            records = []
            for log in logs:
                records.append({
                    "id": log.id,
                    "session_key": log.session_key,
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                    "input_text": log.input_text,
                    "intent_type": log.intent_type,
                    "confidence": log.confidence,
                    "confirmation_status": log.confirmation_status,
                    "execution_status": log.execution_status,
                    "is_undoable": log.is_undoable,
                    "undone": log.undone,
                })

            return {"success": True, "records": records, "total": total, "error": None}

        except Exception as exc:
            _logger.error("Dojo AI /dojo/ai/history failed: %s", exc, exc_info=True)
            return {"success": False, "records": [], "total": 0, "error": str(exc)}

    @http.route("/dojo/ai/intents", type="jsonrpc", auth="user", methods=["GET", "POST"])
    def get_intents(self, role=None, **kwargs):
        """
        Get available intent schemas for the current user's role.
        
        Args:
            role: Optional role override
        
        Returns:
            {
                success: bool,
                intents: list[dict],
                error: str | None
            }
        """
        try:
            if not role:
                role = self._get_user_role()

            Schema = request.env["ai.intent.schema"]
            schemas = Schema.search([("active", "=", True)])

            intents = []
            for schema in schemas:
                if schema.check_role_permission(role):
                    intents.append({
                        "intent_type": schema.intent_type,
                        "name": schema.name,
                        "description": schema.description,
                        "category": schema.category,
                        "requires_confirmation": schema.requires_confirmation,
                        "is_undoable": schema.is_undoable,
                        "supports_bulk": schema.supports_bulk,
                    })

            return {"success": True, "intents": intents, "role": role, "error": None}

        except Exception as exc:
            _logger.error("Dojo AI /dojo/ai/intents failed: %s", exc, exc_info=True)
            return {"success": False, "intents": [], "error": str(exc)}

    @http.route("/dojo/ai/config", type="jsonrpc", auth="user", methods=["GET", "POST"])
    def get_config(self, **kwargs):
        """
        Return client-facing AI assistant configuration values.

        Returns:
            {
                success: bool,
                context_window_turns: int,
                error: str | None
            }
        """
        try:
            turns = request.env["ir.config_parameter"].sudo().get_int(
                "ai_assistant.context_window_turns", 10
            )
            turns = max(1, min(50, turns))
            return {"success": True, "context_window_turns": turns, "error": None}
        except Exception as exc:
            _logger.error("Dojo AI /dojo/ai/config failed: %s", exc, exc_info=True)
            return {"success": True, "context_window_turns": 10, "error": str(exc)}

    # ═══════════════════════════════════════════════════════════════════════════
    # Legacy Endpoints (Backward Compatibility)
    # ═══════════════════════════════════════════════════════════════════════════

    @http.route("/dojo/ai/send_message", type="jsonrpc", auth="user", methods=["POST"])
    def send_message(
        self,
        member_id=None,
        subject="",
        body="",
        send_email=True,
        send_sms=True,
        **kwargs,
    ):
        """
        Execute the confirmed send-to-parent action.
        
        DEPRECATED: Use the new confirmation flow with /confirm endpoint.

        Returns:
            {success, message} or {success: False, error}
        """
        if not member_id:
            return {"success": False, "error": "No member specified."}
        try:
            result = request.env["ai.assistant.service"].send_parent_message(
                int(member_id),
                subject=subject,
                body=body,
                send_email=bool(send_email),
                send_sms=bool(send_sms),
            )
            return result
        except Exception as exc:
            _logger.error("Dojo AI /dojo/ai/send_message failed: %s", exc, exc_info=True)
            return {"success": False, "error": str(exc)}

    # ═══════════════════════════════════════════════════════════════════════════
    # Text-to-Speech (ElevenLabs)
    # ═══════════════════════════════════════════════════════════════════════════

    @http.route("/dojo/ai/speak", type="jsonrpc", auth="user", methods=["POST"])
    def speak(self, text="", **kwargs):
        """
        Convert text to speech using ElevenLabs TTS.

        Args:
            text: Text to synthesise

        Returns:
            {success: True, audio_b64: str, mime: "audio/mpeg"}  on success
            {success: False, error: str}                          on failure
        """
        text = (text or "").strip()
        if not text:
            return {"success": False, "error": "No text provided."}
        # Only instructor / admin may call TTS
        role = self._get_user_role()
        if role not in ("instructor", "admin"):
            return {"success": False, "error": "Access denied."}
        try:
            audio_bytes = request.env["elevenlabs.service"].generate_speech(text)
            if not audio_bytes:
                return {"success": False, "error": "TTS returned empty audio."}
            import base64 as _b64
            return {
                "success": True,
                "audio_b64": _b64.b64encode(audio_bytes).decode("ascii"),
                "mime": "audio/mpeg",
            }
        except Exception as exc:
            _logger.warning("Dojo AI /dojo/ai/speak failed: %s", exc)
            return {"success": False, "error": str(exc)}

    # ═══════════════════════════════════════════════════════════════════════════
    # Helper Methods
    # ═══════════════════════════════════════════════════════════════════════════

    def _get_user_role(self):
        """Determine the current user's role from group membership."""
        user = request.env.user

        # Check for admin role
        if user.has_group("dojo_core.group_dojo_admin"):
            return "admin"

        # Check for instructor role
        if user.has_group("dojo_core.group_dojo_instructor"):
            return "instructor"

        # Default to kiosk (limited permissions)
        return "kiosk"


# ═══════════════════════════════════════════════════════════════════════════════
# Standalone Walkie-Talkie (public URL, PIN-gated)
# ═══════════════════════════════════════════════════════════════════════════════

def _wt_static_ver(*rel_paths):
    """Cache-busting hash for standalone walkie-talkie static files."""
    try:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        mtimes = "".join(
            str(int(os.path.getmtime(os.path.join(base, p))))
            for p in rel_paths
            if os.path.exists(os.path.join(base, p))
        )
        return hashlib.md5(mtimes.encode()).hexdigest()[:8]
    except Exception:
        return "1"


class AiWalkieTalkieController(http.Controller):
    """
    Standalone walkie-talkie SPA — served at /walkie/<token>.
    Fully public routes gated by token + PIN validation on every request.
    No Odoo session required; works outside the backend on any device.
    """

    def _require_walkie(self, token, pin):
        """Validate token + PIN; return the record or raise ValueError."""
        if not token:
            raise ValueError("Missing token.")
        record = request.env["ai.walkie.talkie"].sudo().search(
            [("walkie_token", "=", token), ("active", "=", True)], limit=1
        )
        if not record:
            raise ValueError("Invalid or inactive walkie-talkie link.")
        if not record.walkie_pin:
            raise ValueError("This walkie-talkie has no PIN set. Ask an admin to configure it.")
        if (pin or "") != record.walkie_pin:
            raise ValueError("Incorrect PIN.")
        return record

    # ── SPA shell ──────────────────────────────────────────────────────────────

    @http.route("/walkie/<string:token>", auth="public", type="http", methods=["GET"], csrf=False)
    def walkie_index(self, token, **kw):
        """Serve the standalone walkie-talkie SPA."""
        record = request.env["ai.walkie.talkie"].sudo().search(
            [("walkie_token", "=", token), ("active", "=", True)], limit=1
        )
        if not record:
            return request.make_response(
                "<html><body style='font-family:sans-serif;background:#1a1a2e;color:#e0e0e0;"
                "display:flex;align-items:center;justify-content:center;height:100vh;margin:0'>"
                "<h2>Invalid or inactive walkie-talkie link.</h2></body></html>",
                headers=[("Content-Type", "text/html; charset=utf-8")],
            )
        if not record.walkie_pin:
            return request.make_response(
                "<html><body style='font-family:sans-serif;background:#1a1a2e;color:#e0e0e0;"
                "display:flex;align-items:center;justify-content:center;height:100vh;margin:0'>"
                "<h2>No PIN set for this walkie-talkie. Ask an admin to configure it.</h2></body></html>",
                headers=[("Content-Type", "text/html; charset=utf-8")],
            )

        # PROTOTYPE: route JS/CSS by mode — default mode unchanged
        mode = record.mode or "default"
        _JS_BY_MODE = {
            "default":      "static/src/js/walkie_standalone.js",
            "channel_beta": "static/src/js/walkie_channel_standalone.js",
            "elder_beta":   "static/src/js/walkie_elder_standalone.js",
        }
        _CSS_BY_MODE = {
            "default":      "static/src/css/walkie_standalone.css",
            "channel_beta": "static/src/css/walkie_standalone.css",   # base + channel pills
            "elder_beta":   "static/src/css/walkie_standalone.css",   # base + elder overrides
        }
        js_path  = _JS_BY_MODE.get(mode, _JS_BY_MODE["default"])
        css_path = _CSS_BY_MODE.get(mode, _CSS_BY_MODE["default"])

        ver_js  = _wt_static_ver(js_path)
        ver_css = _wt_static_ver(css_path)
        name_escaped = (record.name or "AI Walkie-Talkie").replace("'", "\\'")

        context_window_turns = request.env["ir.config_parameter"].sudo().get_int(
            "ai_assistant.context_window_turns", 10
        )
        context_window_turns = max(1, min(50, context_window_turns))

        # Extra CSS link for channel/elder prototype overlays
        extra_css = ""
        if mode == "channel_beta":
            ver_ch = _wt_static_ver("static/src/css/walkie_channel.css")
            extra_css = f'    <link rel="stylesheet" href="/ai_assistant/static/src/css/walkie_channel.css?v={ver_ch}"/>\n'
        elif mode == "elder_beta":
            ver_el = _wt_static_ver("static/src/css/walkie_elder.css")
            extra_css = f'    <link rel="stylesheet" href="/ai_assistant/static/src/css/walkie_elder.css?v={ver_el}"/>\n'

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no"/>
    <meta name="robots" content="noindex,nofollow"/>
    <title>{record.name} — Walkie-Talkie</title>
    <link rel="stylesheet" href="/web/static/src/libs/fontawesome/css/font-awesome.css"/>
    <link rel="stylesheet" href="/ai_assistant/static/src/css/walkie_standalone.css?v={ver_css}"/>
{extra_css}</head>
<body>
    <div id="wt-root"></div>
    <script>
        window.WT_TOKEN = '{token}';
        window.WT_NAME  = '{name_escaped}';
        window.WT_CONFIG = {{ context_window_turns: {context_window_turns}, mode: '{mode}' }};
        function _wtShowError(msg) {{
            var el = document.getElementById('wt-root');
            if (el) el.innerHTML = '<pre style="color:red;background:#111;padding:20px;font-size:13px;white-space:pre-wrap;margin:0">' + msg + '</pre>';
        }}
        window.onerror = function(msg, src, line, col, err) {{
            _wtShowError('JS ERROR:\\n' + msg + '\\nSource: ' + src + ':' + line + ':' + col);
        }};
        window.addEventListener('unhandledrejection', function(ev) {{
            var r = ev.reason;
            _wtShowError('ASYNC ERROR (mount/render):\\n' + (r && r.stack ? r.stack : String(r)));
        }});
    </script>
    <script src="/web/static/lib/owl/owl.js"></script>
    <script src="/ai_assistant/static/src/js/{js_path.split('/')[-1]}?v={ver_js}"></script>
</body>
</html>"""
        return request.make_response(html, headers=[("Content-Type", "text/html; charset=utf-8")])

    # ── Auth ───────────────────────────────────────────────────────────────────

    @http.route("/walkie/<string:token>/auth", type="jsonrpc", auth="public", methods=["POST"], csrf=False)
    def walkie_auth(self, token, pin="", **kw):
        """Validate token + PIN. Returns {success: true} or {success: false, error: str}."""
        try:
            self._require_walkie(token, pin)
            return {"success": True}
        except ValueError as e:
            return {"success": False, "error": str(e)}

    # ── Text query ─────────────────────────────────────────────────────────────

    @http.route("/walkie/<string:token>/text", type="jsonrpc", auth="public", methods=["POST"], csrf=False)
    def walkie_text(self, token, pin="", text="", conversation_history=None, channel=None, **kw):
        try:
            record = self._require_walkie(token, pin)
        except ValueError as e:
            return {"success": False, "state": "error", "error": str(e)}

        text = (text or "").strip()
        if not text:
            return {"success": False, "state": "error", "error": "No text provided."}

        if isinstance(conversation_history, str):
            try:
                conversation_history = json.loads(conversation_history)
            except Exception:
                conversation_history = None

        try:
            record.sudo().write({"last_used": _dt.utcnow()})
            assistant = request.env["ai.assistant.service"].sudo()
            return assistant.handle_command(
                text, role="instructor", input_type="text",
                conversation_history=conversation_history,
                channel=channel or None,
            )
        except Exception as exc:
            _logger.error("Walkie /text failed: %s", exc, exc_info=True)
            return {"success": False, "state": "error", "error": str(exc)}

    # ── Voice query ────────────────────────────────────────────────────────────

    @http.route("/walkie/<string:token>/voice", type="http", auth="public", methods=["POST"], csrf=False)
    def walkie_voice(self, token, **kw):
        def _json_resp(data, status=200):
            return request.make_response(
                json.dumps(data, ensure_ascii=False).encode("utf-8"),
                headers=[("Content-Type", "application/json; charset=utf-8")],
                status=status,
            )

        pin = request.httprequest.form.get("pin", "")
        try:
            record = self._require_walkie(token, pin)
        except ValueError as e:
            return _json_resp({"success": False, "state": "error", "error": str(e)}, 403)

        try:
            audio_file = request.httprequest.files.get("audio")
            if not audio_file:
                return _json_resp({"success": False, "state": "error", "error": "No audio file provided."}, 400)
            audio_bytes = audio_file.read()
            if not audio_bytes:
                return _json_resp({"success": False, "state": "error", "error": "Empty audio file."}, 400)

            attachment = None
            try:
                attachment = request.env["ir.attachment"].sudo().create({
                    "name": f"walkie_voice_{audio_file.filename or 'audio.webm'}",
                    "datas": base64.b64encode(audio_bytes),
                    "mimetype": audio_file.content_type or "audio/webm",
                    "res_model": "ai.action.log",
                })
            except Exception as e:
                _logger.warning("Could not save walkie audio attachment: %s", e)

            lang = record.stt_language or "en"
            try:
                transcribed = request.env["elevenlabs.service"].sudo().transcribe_audio(
                    audio_bytes, language=lang
                )
            except Exception as exc:
                _logger.error("Walkie STT failed: %s", exc)
                return _json_resp({"success": False, "state": "error",
                                   "error": "Speech-to-text failed. Please configure ElevenLabs in Settings."})

            transcribed = (transcribed or "").strip()
            if not transcribed:
                return _json_resp({"success": False, "state": "error",
                                   "error": "Could not understand the audio. Please try again."})

            history_raw = request.httprequest.form.get("conversation_history")
            conversation_history = None
            if history_raw:
                try:
                    conversation_history = json.loads(history_raw)
                except Exception:
                    pass

            channel = request.httprequest.form.get("channel") or None

            record.sudo().write({"last_used": _dt.utcnow()})
            assistant = request.env["ai.assistant.service"].sudo()
            result = assistant.handle_command(
                transcribed,
                role="instructor",
                input_type="voice",
                audio_attachment_id=attachment.id if attachment else None,
                conversation_history=conversation_history,
                channel=channel,
            )
            result["transcribed"] = transcribed

            # ── Post to Discuss (Elder / Channel Beta modes) ──────────────
            if record.mode in ("elder_beta", "channel_beta"):
                try:
                    source_lang = record.stt_language or "en"
                    if record.discuss_post_as_id:
                        author_id = record.discuss_post_as_id.id
                    else:
                        odoobot = request.env.ref("base.partner_root", raise_if_not_found=False)
                        author_id = odoobot.id if odoobot else None
                    record.sudo().post_voice_to_discuss(
                        audio_bytes, transcribed,
                        channel_type=channel, author_id=author_id,
                        source_lang=source_lang,
                    )
                    ai_text = result.get("response") or result.get("confirmation_prompt") or ""
                    if ai_text:
                        record.sudo().post_ai_response_to_discuss(
                            ai_text, channel_type=channel,
                            source_lang=source_lang,
                        )
                except Exception:
                    _logger.warning("Discuss posting failed (walkie token=%s)", token, exc_info=True)

            return _json_resp(result)

        except Exception as exc:
            _logger.error("Walkie /voice failed: %s", exc, exc_info=True)
            return _json_resp({"success": False, "state": "error", "error": str(exc)}, 500)

    # ── Confirm action ─────────────────────────────────────────────────────────

    @http.route("/walkie/<string:token>/confirm", type="jsonrpc", auth="public", methods=["POST"], csrf=False)
    def walkie_confirm(self, token, pin="", session_key="", confirmed=True, **kw):
        try:
            self._require_walkie(token, pin)
        except ValueError as e:
            return {"success": False, "state": "error", "error": str(e)}
        if not session_key:
            return {"success": False, "state": "error", "error": "No session_key provided."}
        try:
            assistant = request.env["ai.assistant.service"].sudo()
            return assistant.execute_confirmed(session_key, confirmed=bool(confirmed))
        except Exception as exc:
            _logger.error("Walkie /confirm failed: %s", exc, exc_info=True)
            return {"success": False, "state": "error", "error": str(exc)}

    # ── Text-to-Speech ─────────────────────────────────────────────────────────

    @http.route("/walkie/<string:token>/speak", type="jsonrpc", auth="public", methods=["POST"], csrf=False)
    def walkie_speak(self, token, pin="", text="", **kw):
        try:
            self._require_walkie(token, pin)
        except ValueError as e:
            return {"success": False, "error": str(e)}
        text = (text or "").strip()
        if not text:
            return {"success": False, "error": "No text provided."}
        try:
            audio_bytes = request.env["elevenlabs.service"].sudo().generate_speech(text)
            if not audio_bytes:
                return {"success": False, "error": "TTS returned empty audio."}
            return {
                "success": True,
                "audio_b64": base64.b64encode(audio_bytes).decode("ascii"),
                "mime": "audio/mpeg",
            }
        except Exception as exc:
            _logger.warning("Walkie /speak failed: %s", exc)
            return {"success": False, "error": str(exc)}
