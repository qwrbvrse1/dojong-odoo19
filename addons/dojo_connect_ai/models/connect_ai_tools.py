# -*- coding: utf-8 -*-

"""
Single service method backing the ElevenLabs agent tool endpoint.

Routes the caller's natural-language request through the dojo_assistant
AI intent engine, which handles 57+ intents (schedule lookups, member
queries, trial bookings, enrollment, etc.).

Transfer-to-human requests are detected and handled via Twilio REST API.
"""

import logging
from urllib.parse import urljoin

from odoo import api, models

_logger = logging.getLogger(__name__)

# Phrases that signal the caller wants a human
_TRANSFER_SIGNALS = (
    "transfer", "speak to a person", "speak to someone",
    "talk to a human", "talk to someone", "real person",
    "operator", "front desk", "receptionist",
)


class ConnectAiTools(models.AbstractModel):
    _name = "connect.ai.tools"
    _description = "AI Agent Tool Service"

    # ------------------------------------------------------------------
    # Main entry point — single tool for everything
    # ------------------------------------------------------------------

    @api.model
    def ask_assistant(self, user_message, caller_phone="", call_sid="", agent_id=False):
        """Route the caller's request through dojo_assistant.

        1. Check if the message is a transfer request → handle via Twilio API
        2. Otherwise, pass to ai.assistant.service.handle_command()
        3. If the intent requires confirmation, auto-confirm (voice callers
           can't click buttons — the ElevenLabs agent handles confirmation
           conversationally)
        4. Return a plain-text response for the ElevenLabs agent to speak
        """
        # ── Transfer detection ───────────────────────────────────────
        msg_lower = user_message.lower()
        if any(signal in msg_lower for signal in _TRANSFER_SIGNALS):
            if call_sid and agent_id:
                result = self._transfer_call(call_sid, agent_id)
                if result.get("success"):
                    return {"response": "Transferring you now. One moment please."}
                return {"response": result.get("error", "I'm unable to transfer right now. Please try calling back.")}
            return {"response": "I'd be happy to transfer you, but I'm unable to do so right now. Please try calling back during business hours."}

        # ── Enrich message with caller context ───────────────────────
        enriched = user_message
        if caller_phone:
            enriched = f"[Caller phone: {caller_phone}] {user_message}"

        # ── Route through dojo_assistant ─────────────────────────────
        try:
            service = self.env["ai.assistant.service"].sudo()
            result = service.handle_command(
                text=enriched,
                role="kiosk",       # safe role for phone callers
                input_type="text",
            )
        except Exception:
            _logger.exception("ask_assistant: handle_command failed")
            return {"response": "I'm sorry, I wasn't able to process that request. Could you try asking in a different way?"}

        if not result.get("success"):
            error = result.get("error", "")
            response_text = result.get("response", "")
            return {"response": response_text or error or "I'm sorry, I didn't understand that. Could you rephrase?"}

        state = result.get("state", "")

        # ── Auto-executed (read-only intents like schedule lookups) ───
        if result.get("auto_executed") or state == "executed":
            return {"response": result.get("response", "Done.")}

        # ── Needs confirmation — auto-confirm for voice callers ──────
        if state == "pending_confirmation" and result.get("session_key"):
            try:
                execution = service.execute_confirmed(
                    session_key=result["session_key"],
                    confirmed=True,
                )
                if execution.get("success"):
                    # Use the confirmation prompt as context + execution result
                    exec_response = execution.get("response", "")
                    confirmation = result.get("confirmation_prompt", "")
                    return {"response": exec_response or f"Done. {confirmation}"}
                return {"response": execution.get("error", "I wasn't able to complete that action.")}
            except Exception:
                _logger.exception("ask_assistant: execute_confirmed failed")
                return {"response": "I understood your request but ran into an issue completing it. Please try again."}

        # ── Conversational response (no action needed) ───────────────
        return {"response": result.get("response", result.get("confirmation_prompt", "I'm here to help. What would you like to know?"))}

    # ------------------------------------------------------------------
    # Internal: Transfer call to human via Twilio REST API
    # ------------------------------------------------------------------

    @api.model
    def _transfer_call(self, call_sid, agent_id):
        """Update a live Twilio call to redirect to a human."""
        agent = self.env["connect.ai.agent"].sudo().browse(agent_id)
        if not agent.exists():
            return {"success": False, "error": "AI agent not found"}

        if not agent.fallback_user_id:
            return {"success": False, "error": "No one is available to take calls right now."}

        try:
            client = self.env["connect.settings"].sudo().get_client()

            from twilio.twiml.voice_response import VoiceResponse, Dial, Client
            api_url = self.env["connect.settings"].sudo().get_param("api_url")
            status_url = urljoin(api_url, "twilio/webhook/callstatus")
            record_url = urljoin(api_url, "twilio/webhook/recordingstatus")

            response = VoiceResponse()
            response.say(
                "Please hold while I transfer you to a team member.",
                voice="Polly.Joanna",
            )

            user = agent.fallback_user_id
            dial_kwargs = {"timeout": user.sip_ring_timeout or 30}
            if user.record_calls:
                dial_kwargs["record"] = "record-from-answer-dual"
                dial_kwargs["recordingStatusCallback"] = record_url

            dial = Dial(**dial_kwargs)

            if user.sip_enabled:
                dial.sip(
                    f"sip:{user.uri}",
                    statusCallbackEvent="initiated answered completed",
                    statusCallback=status_url,
                )
            elif user.client_enabled:
                client_verb = Client(
                    statusCallbackEvent="initiated answered completed",
                    statusCallback=status_url,
                )
                client_verb.identity(user.username)
                dial.append(client_verb)

            response.append(dial)

            if agent.voicemail_enabled:
                response.say(
                    "No one is available right now. Please leave a message after the beep.",
                    voice="Polly.Joanna",
                )
                response.record(max_length=120, finish_on_key="#", play_beep=True)
            else:
                response.say("Sorry, no one is available. Please try again later.")
                response.hangup()

            client.calls(call_sid).update(twiml=str(response))

            return {"success": True, "message": "Call transferred"}

        except Exception as e:
            _logger.exception("Transfer call failed:")
            return {"success": False, "error": str(e)}
