# -*- coding: utf-8 -*-

import hashlib
import hmac
import json
import logging
from urllib.parse import urljoin

from odoo import api, fields, models
from odoo.exceptions import UserError
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream

_logger = logging.getLogger(__name__)


class ConnectAiAgent(models.Model):
    _name = "connect.ai.agent"
    _description = "AI Voice Agent"
    _order = "name"

    name = fields.Char(required=True, help="Display name (e.g. Kai)")
    active = fields.Boolean(default=True)

    # ── ElevenLabs configuration ─────────────────────────────────────
    elevenlabs_agent_id = fields.Char(
        string="ElevenLabs Agent ID",
        required=True,
        help="Agent ID from the ElevenLabs Conversational AI dashboard.",
    )
    system_prompt = fields.Text(
        string="System Prompt (reference)",
        help="Read-only reference copy of the prompt configured in ElevenLabs.",
    )

    # ── Call handling ────────────────────────────────────────────────
    fallback_user_id = fields.Many2one(
        "connect.user",
        string="Fallback User",
        ondelete="set null",
        help="Human to ring when the caller requests a transfer.",
    )
    voicemail_enabled = fields.Boolean(
        default=True,
        help="Allow voicemail if the fallback user doesn't answer.",
    )

    # ── CRM automation ──────────────────────────────────────────────
    auto_create_lead = fields.Boolean(
        string="Auto-Create CRM Lead",
        default=True,
        help="Create a CRM lead after every AI conversation.",
    )

    # ── Webhook security ────────────────────────────────────────────
    webhook_secret = fields.Char(
        string="Tool API Key (X-Api-Key)",
        help="Secret token ElevenLabs sends in the X-Api-Key header when calling Odoo tools.",
        groups="base.group_erp_manager",
    )
    elevenlabs_webhook_secret = fields.Char(
        string="ElevenLabs Signing Secret",
        help="The wsec_... secret from ElevenLabs post-call webhook config. Used to verify incoming webhook signatures.",
        groups="base.group_erp_manager",
    )

    # ── Stats ────────────────────────────────────────────────────────
    call_count = fields.Integer(
        compute="_compute_call_count",
        string="Calls Handled",
    )
    lead_count = fields.Integer(
        compute="_compute_lead_count",
        string="Leads Created",
    )

    def _compute_call_count(self):
        for rec in self:
            rec.call_count = self.env["connect.call"].search_count(
                [("ai_agent_id", "=", rec.id)]
            )

    def _compute_lead_count(self):
        for rec in self:
            rec.lead_count = self.env["crm.lead"].search_count(
                [("ai_agent_id", "=", rec.id)]
            )

    # ------------------------------------------------------------------
    # Stat button actions
    # ------------------------------------------------------------------

    def action_view_calls(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "AI Calls",
            "res_model": "connect.call",
            "view_mode": "list,form",
            "domain": [("ai_agent_id", "=", self.id)],
            "context": {"default_ai_agent_id": self.id},
        }

    def action_view_leads(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "AI Leads",
            "res_model": "crm.lead",
            "view_mode": "list,form",
            "domain": [("ai_agent_id", "=", self.id)],
            "context": {"default_ai_agent_id": self.id},
        }

    # ------------------------------------------------------------------
    # TwiML rendering — returns <Connect><Stream> pointing to ElevenLabs
    # ------------------------------------------------------------------

    def render_twiml(self, request_params):
        """Build TwiML that bridges the Twilio call to ElevenLabs Conversational AI.

        Uses Twilio's <Connect><Stream> verb to open a bidirectional audio
        WebSocket directly from Twilio to ElevenLabs — no WebSocket server
        needed in Odoo.
        """
        self.ensure_one()
        response = VoiceResponse()

        # Build the ElevenLabs WebSocket URL with dynamic context
        caller_phone = request_params.get("From", "")
        caller_name = self._resolve_caller_name(caller_phone)

        # ElevenLabs Twilio Media Stream endpoint — agent_id in the path
        stream_url = (
            f"wss://api.elevenlabs.io/v1/convai/conversation"
            f"?agent_id={self.elevenlabs_agent_id}"
        )

        connect = Connect()
        # track="both_tracks" enables bidirectional audio (required for TTS to reach caller)
        stream = Stream(url=stream_url, track="both_tracks")

        # Pass caller metadata as Stream parameters (available inside ElevenLabs agent)
        stream.parameter(name="caller_phone", value=caller_phone)
        if caller_name:
            stream.parameter(name="caller_name", value=caller_name)
        stream.parameter(name="call_sid", value=request_params.get("CallSid", ""))

        # Pass the Odoo tool base URL so the agent knows where to call back
        api_url = self.env["connect.settings"].sudo().get_param("api_url")
        if api_url:
            stream.parameter(name="odoo_api_url", value=api_url)

        connect.append(stream)
        response.append(connect)

        # After the stream ends (AI hangs up or stream closes), say goodbye.
        # Live transfers during the call are handled via the transfer tool
        # endpoint, which updates the Twilio call with new TwiML.
        response.say("Thank you for calling. Goodbye!", voice="Polly.Joanna")
        response.hangup()

        return str(response)

    def _resolve_caller_name(self, phone):
        """Look up caller by phone number and return display name if found."""
        if not phone:
            return ""
        partner = self.env["res.partner"].sudo().get_partner_by_number(phone)
        return partner.name if partner else ""

    # ------------------------------------------------------------------
    # Post-conversation processing (called from webhook controller)
    # ------------------------------------------------------------------

    def process_conversation_end(self, data):
        """Process the ElevenLabs post-conversation webhook payload.

        Creates/updates CRM lead, posts transcript to chatter, links to
        the connect.call record.
        """
        self.ensure_one()
        conversation_id = data.get("conversation_id", "")
        call_sid = data.get("call_sid", "")
        transcript_data = data.get("transcript", [])
        analysis = data.get("analysis", {})
        caller_phone = data.get("caller_phone", "")

        # Format transcript
        transcript_lines = []
        for turn in transcript_data:
            role = turn.get("role", "unknown").capitalize()
            text = turn.get("message", "")
            if text:
                transcript_lines.append(f"<b>{role}:</b> {text}")
        transcript_html = "<br/>".join(transcript_lines)
        transcript_plain = "\n".join(
            f"{t.get('role', '?')}: {t.get('message', '')}"
            for t in transcript_data
            if t.get("message")
        )

        # Find matching call record
        call = False
        if call_sid:
            channel = self.env["connect.channel"].sudo().search(
                [("sid", "=", call_sid)], limit=1
            )
            if channel and channel.call:
                call = channel.call

        # Update call with AI data
        if call:
            call.sudo().write({
                "ai_conversation_id": conversation_id,
                "ai_transcript": transcript_plain,
                "ai_agent_id": self.id,
            })

        # Resolve caller partner
        partner = False
        if caller_phone:
            partner = self.env["res.partner"].sudo().get_partner_by_number(
                caller_phone
            )

        # Find or create CRM lead
        lead = self._find_or_create_lead(
            caller_phone=caller_phone,
            partner=partner,
            call=call,
            analysis=analysis,
            transcript_html=transcript_html,
        )

        # Link lead to call
        if call and lead:
            call.sudo().write({"ai_lead_id": lead.id})

        # Log to dojo.ai.action.log if available
        self._log_ai_action(conversation_id, transcript_plain, lead)

        return {"success": True, "lead_id": lead.id if lead else False}

    def _find_or_create_lead(
        self, caller_phone, partner, call, analysis, transcript_html
    ):
        """Find existing open lead for this caller or create a new one."""
        if not self.auto_create_lead:
            return False

        Lead = self.env["crm.lead"].sudo()
        medium = self.env.ref(
            "dojo_connect_ai.utm_medium_voice_ai", raise_if_not_found=False
        )
        tag_ai = self.env.ref(
            "dojo_connect_ai.crm_tag_ai_receptionist", raise_if_not_found=False
        )
        tag_voice = self.env.ref(
            "dojo_connect_ai.crm_tag_voice_inquiry", raise_if_not_found=False
        )
        stage_new = self.env.ref(
            "dojo_crm.crm_stage_new_lead", raise_if_not_found=False
        )

        # Check for existing open lead with same phone (avoid duplicates)
        domain = [("active", "=", True)]
        if partner:
            domain.append(("partner_id", "=", partner.id))
        elif caller_phone:
            domain.append(("phone", "=", caller_phone))
        domain.append(("stage_id.is_won", "=", False))

        existing_lead = Lead.search(domain, order="create_date desc", limit=1)

        if existing_lead:
            # Post transcript to existing lead's chatter
            existing_lead.message_post(
                body=f"<p><strong>AI Call Transcript (Kai):</strong></p>{transcript_html}",
                subject="AI Receptionist Call",
                message_type="comment",
                subtype_xmlid="mail.mt_note",
            )
            return existing_lead

        # Build lead values
        contact_name = partner.name if partner else ""
        intent_summary = analysis.get("summary", "Inbound call to AI receptionist")

        lead_vals = {
            "name": f"AI Call — {contact_name or caller_phone or 'Unknown'}",
            "phone": caller_phone,
            "contact_name": contact_name,
            "description": intent_summary,
            "ai_agent_id": self.id,
        }
        if partner:
            lead_vals["partner_id"] = partner.id
            lead_vals["email_from"] = partner.email
        if medium:
            lead_vals["medium_id"] = medium.id
        if stage_new:
            lead_vals["stage_id"] = stage_new.id

        tag_ids = []
        if tag_ai:
            tag_ids.append(tag_ai.id)
        if tag_voice:
            tag_ids.append(tag_voice.id)
        if tag_ids:
            lead_vals["tag_ids"] = [(6, 0, tag_ids)]

        lead = Lead.create(lead_vals)

        # Post transcript to new lead's chatter
        if transcript_html:
            lead.message_post(
                body=f"<p><strong>AI Call Transcript (Kai):</strong></p>{transcript_html}",
                subject="AI Receptionist Call",
                message_type="comment",
                subtype_xmlid="mail.mt_note",
            )

        return lead

    def _log_ai_action(self, conversation_id, transcript_plain, lead):
        """Log to dojo.ai.action.log for audit trail."""
        ActionLog = self.env.get("dojo.ai.action.log")
        if ActionLog is None:
            return
        try:
            ActionLog.sudo().create({
                "input_text": transcript_plain[:500] if transcript_plain else "",
                "input_type": "voice",
                "intent_type": "ai_call_processed",
                "confidence": 1.0,
                "execution_status": "success",
                "execution_result": json.dumps({
                    "conversation_id": conversation_id,
                    "lead_id": lead.id if lead else False,
                }),
                "role": "admin",
            })
        except Exception:
            _logger.warning("Failed to log AI call action", exc_info=True)

    # ------------------------------------------------------------------
    # Missed call handling
    # ------------------------------------------------------------------

    def create_missed_call_lead(self, caller_phone, call=False):
        """Create a CRM lead from a missed/unanswered call."""
        self.ensure_one()

        Lead = self.env["crm.lead"].sudo()
        medium = self.env.ref(
            "dojo_connect_ai.utm_medium_voice_ai", raise_if_not_found=False
        )
        tag_missed = self.env.ref(
            "dojo_connect_ai.crm_tag_missed_call", raise_if_not_found=False
        )
        stage_new = self.env.ref(
            "dojo_crm.crm_stage_new_lead", raise_if_not_found=False
        )

        # Check for existing open lead
        partner = False
        if caller_phone:
            partner = self.env["res.partner"].sudo().get_partner_by_number(
                caller_phone
            )

        domain = [("active", "=", True), ("stage_id.is_won", "=", False)]
        if partner:
            domain.append(("partner_id", "=", partner.id))
        elif caller_phone:
            domain.append(("phone", "=", caller_phone))
        else:
            return False

        existing_lead = Lead.search(domain, order="create_date desc", limit=1)

        if existing_lead:
            existing_lead.message_post(
                body=f"<p>Missed call from <b>{caller_phone}</b></p>",
                subject="Missed Call",
                message_type="comment",
                subtype_xmlid="mail.mt_note",
            )
            # Create follow-up activity
            if self.fallback_user_id and self.fallback_user_id.user:
                existing_lead.activity_schedule(
                    "mail.mail_activity_data_call",
                    summary=f"Return call to {caller_phone}",
                    user_id=self.fallback_user_id.user.id,
                )
            return existing_lead

        contact_name = partner.name if partner else ""
        lead_vals = {
            "name": f"Missed Call — {contact_name or caller_phone}",
            "phone": caller_phone,
            "contact_name": contact_name,
            "description": f"Missed incoming call. Caller did not reach the AI agent or hung up.",
            "ai_agent_id": self.id,
        }
        if partner:
            lead_vals["partner_id"] = partner.id
            lead_vals["email_from"] = partner.email
        if medium:
            lead_vals["medium_id"] = medium.id
        if stage_new:
            lead_vals["stage_id"] = stage_new.id
        if tag_missed:
            lead_vals["tag_ids"] = [(6, 0, [tag_missed.id])]

        lead = Lead.create(lead_vals)

        if call:
            call.sudo().write({"ai_lead_id": lead.id})

        # Create follow-up activity
        if self.fallback_user_id and self.fallback_user_id.user:
            lead.activity_schedule(
                "mail.mail_activity_data_call",
                summary=f"Return call to {caller_phone}",
                user_id=self.fallback_user_id.user.id,
            )

        return lead

    # ------------------------------------------------------------------
    # Webhook signature validation
    # ------------------------------------------------------------------

    def verify_webhook_signature(self, payload_body, signature_header):
        """Validate ElevenLabs post-call webhook signature.

        ElevenLabs signs webhooks using the format:
            X-ElevenLabs-Signature: t=<timestamp>,v0=<hmac_sha256_hex>

        The signed payload is: "<timestamp>,<raw_body>"
        """
        self.ensure_one()
        if not self.elevenlabs_webhook_secret:
            return True  # No secret configured — skip validation (dev mode)

        if not signature_header:
            return False

        # Parse "t=123456789,v0=abcdef..."
        try:
            parts = dict(part.split("=", 1) for part in signature_header.split(","))
            timestamp = parts.get("t", "")
            v0 = parts.get("v0", "")
        except (ValueError, AttributeError):
            return False

        if not timestamp or not v0:
            return False

        # Signed payload = "<timestamp>.<raw_body>"
        body_str = payload_body if isinstance(payload_body, str) else payload_body.decode()
        signed_payload = f"{timestamp}.{body_str}"

        expected = hmac.new(
            self.elevenlabs_webhook_secret.encode(),
            signed_payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, v0)
