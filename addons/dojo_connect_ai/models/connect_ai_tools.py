# -*- coding: utf-8 -*-

"""
Single service method backing the ElevenLabs agent tool endpoint.

Routes the caller's natural-language request through the ai_assistant
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
        """Route the caller's request through ai_assistant.

        1. Resolve caller identity: instructor → role='instructor'; member/guardian → role='kiosk' + context
        2. Check if the message is a transfer request → handle via Twilio API
        3. Otherwise, pass to ai.assistant.service.handle_command() with correct role
        4. If the intent requires confirmation, auto-confirm (voice callers
           can't click buttons — the ElevenLabs agent handles confirmation
           conversationally)
        5. Return a plain-text response for the ElevenLabs agent to speak
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

        # ── Caller identity resolution ───────────────────────────────
        role = "caller"   # default for all phone callers
        context_tags = []

        if caller_phone:
            context_tags.append(f"Caller phone: {caller_phone}")
            try:
                caller_partner = self.env["res.partner"].sudo().get_partner_by_number(caller_phone)
                if caller_partner and caller_partner.exists():
                    # 1. Check if this is a dojo instructor
                    instructor = self.env["dojo.instructor.profile"].sudo().search(
                        [("partner_id", "=", caller_partner.id), ("active", "=", True)],
                        limit=1,
                    )
                    if instructor:
                        role = "instructor"
                        context_tags.append(f"Caller is Instructor: {instructor.name}")
                        context_tags.append("Authorization: full access to all member data and commands")
                    else:
                        # 2. Direct dojo member
                        member = self.env["dojo.member"].sudo().search(
                            [("partner_id", "=", caller_partner.id)], limit=1
                        )
                        if member.exists():
                            role = "caller"
                            context_tags.append(
                                f"Caller is Member: {member.name} (Member ID: {member.id})"
                            )
                            context_tags.append(
                                "Authorization: caller may only access their own member data"
                            )
                        else:
                            # 3. Guardian — find their household children who are students
                            student_names = []
                            if getattr(caller_partner, "is_guardian", False):
                                household = (
                                    caller_partner.parent_id
                                    if caller_partner.parent_id
                                    and getattr(caller_partner.parent_id, "is_household", False)
                                    else None
                                )
                                if household:
                                    student_partners = household.child_ids.filtered(
                                        lambda p: getattr(p, "is_student", False)
                                    )
                                    student_members = self.env["dojo.member"].sudo().search(
                                        [("partner_id", "in", student_partners.ids)]
                                    )
                                    student_names = student_members.mapped("name")

                            if student_names:
                                role = "caller"
                                names_str = ", ".join(student_names)
                                context_tags.append(
                                    f"Caller is Guardian of: {names_str}"
                                )
                                context_tags.append(
                                    f"Authorization: caller may access data for their students ({names_str}) only"
                                )
                            else:
                                role = "caller"
                                context_tags.append(
                                    f"Caller: {caller_partner.name or caller_phone} (no member or guardian record found)"
                                )
                                context_tags.append(
                                    "Authorization: no member record — provide general information and offer to book a trial"
                                )
                else:
                    role = "caller"
                    context_tags.append("Caller: unrecognized number — no member record found")
                    context_tags.append(
                        "Authorization: no member record — provide general information and offer to book a trial"
                    )
            except Exception:
                _logger.warning("ask_assistant: caller identity lookup failed for %s", caller_phone)
                context_tags.append(f"Caller phone: {caller_phone}")

        # ── Enrich message with caller context ───────────────────────
        prefix = " ".join(f"[{tag}]" for tag in context_tags)
        enriched = f"{prefix} {user_message}".strip() if prefix else user_message

        # ── Route through ai_assistant ─────────────────────────────
        try:
            service = self.env["ai.assistant.service"].sudo()
            result = service.handle_command(
                text=enriched,
                role=role,
                input_type="text",
            )
        except Exception:
            _logger.exception("ask_assistant: handle_command failed")
            return {"response": "I'm sorry, I wasn't able to process that request. Could you try asking in a different way?"}

        if not result.get("success"):
            return {"response": self._shape_error_response(result)}

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
                    exec_response = execution.get("response", "")
                    confirmation = result.get("confirmation_prompt", "")
                    return {"response": exec_response or f"Done. {confirmation}"}
                return {"response": self._shape_error_response(execution)}
            except Exception:
                _logger.exception("ask_assistant: execute_confirmed failed")
                return {"response": "I understood your request but ran into an issue completing it. Please try again."}

        # ── Conversational response (no action needed) ───────────────
        return {"response": result.get("response", result.get("confirmation_prompt", "I'm here to help. What would you like to know?"))}

    @api.model
    def _shape_error_response(self, result):
        """Convert an unsuccessful result dict into a natural spoken response."""
        error = result.get("error", "")
        response_text = result.get("response", "")
        state = result.get("state", "")

        # Permission denied (role blocked the intent)
        if "permission" in error.lower() or "not allowed" in error.lower() or state == "permission_denied":
            return "I'm sorry, I can only provide information related to your own account."

        # Record not found
        if "not found" in error.lower() or "no record" in error.lower():
            return "I wasn't able to find that record. Could you confirm the name or spelling?"

        # Missing information needed to proceed
        if "missing" in error.lower() or "required" in error.lower() or state == "needs_info":
            detail = response_text or "more details"
            return f"I need a bit more information to help with that. {detail}"

        # Use the response or error text if it's already human-readable
        if response_text:
            return response_text
        if error and len(error) < 200:
            return error

        return "I understood your request but ran into an issue. Would you like me to transfer you to a team member?"

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
