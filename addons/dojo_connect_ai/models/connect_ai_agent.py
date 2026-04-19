# -*- coding: utf-8 -*-

import hashlib
import hmac
import json
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ConnectAiAgent(models.Model):
    _name = "connect.ai.agent"
    _description = "AI Voice Agent"
    _order = "name"

    name = fields.Char(required=True, help="Display name (e.g. Kai)")
    active = fields.Boolean(default=True)

    # ── ElevenLabs configuration ─────────────────────────────────────
    synced_agent_id = fields.Many2one(
        "dojo.elevenlabs.agent",
        string="ElevenLabs Agent",
        help="Select a synced agent from ElevenLabs. Sync via Connect → Settings → API Keys.",
    )
    elevenlabs_agent_id = fields.Char(
        string="Agent ID",
        compute="_compute_elevenlabs_agent_id",
        inverse="_inverse_elevenlabs_agent_id",
        store=True,
        required=True,
        help="Auto-filled from synced agent, or enter manually.",
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

    @api.depends("synced_agent_id", "synced_agent_id.elevenlabs_id")
    def _compute_elevenlabs_agent_id(self):
        for rec in self:
            if rec.synced_agent_id:
                rec.elevenlabs_agent_id = rec.synced_agent_id.elevenlabs_id
            elif not rec.elevenlabs_agent_id:
                rec.elevenlabs_agent_id = ""

    def _inverse_elevenlabs_agent_id(self):
        """Allow manual entry of agent ID without a synced agent."""
        pass

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
    # Post-conversation processing (called from webhook controller)
    # ------------------------------------------------------------------

    def process_conversation_end(self, data):
        """Process the ElevenLabs post-conversation webhook payload.

        Creates/updates CRM lead, posts transcript to chatter, links to
        the connect.call record.
        """
        self.ensure_one()
        # caller_phone and call_sid may come from the top-level payload (legacy flat format)
        # or from conversation_initiation_client_data.dynamic_variables (set by our
        # initiation webhook). Define the dynamic_variables lookup first.
        _dyn_vars = (
            data.get("conversation_initiation_client_data", {})
                .get("dynamic_variables", {})
        )
        conversation_id = data.get("conversation_id", "")
        call_sid = data.get("call_sid", "") or _dyn_vars.get("call_sid", "")
        caller_phone = data.get("caller_phone", "") or _dyn_vars.get("caller_phone", "")
        transcript_data = data.get("transcript", [])
        analysis = data.get("analysis", {})

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

        # Resolve caller partner
        partner = False
        if caller_phone:
            partner = self.env["res.partner"].sudo().get_partner_by_number(
                caller_phone
            )

        # Build call summary HTML from analysis + transcript
        summary_text = analysis.get("summary", "")
        call_summary_html = ""
        if summary_text:
            call_summary_html += f"<p><strong>Summary:</strong> {summary_text}</p>"
        if transcript_html:
            call_summary_html += (
                f"<p><strong>Transcript:</strong></p>"
                f"<p>{transcript_html}</p>"
            )

        # Find matching call record (legacy path — when Twilio still routes
        # through Odoo and creates a channel)
        Call = self.env["connect.call"].sudo()
        call = False
        if call_sid:
            channel = self.env["connect.channel"].sudo().search(
                [("sid", "=", call_sid)], limit=1
            )
            if channel and channel.call:
                call = channel.call

        # Also check if we already logged this conversation (avoid duplicates
        # on webhook retries)
        if not call and conversation_id:
            call = Call.search(
                [("ai_conversation_id", "=", conversation_id)], limit=1
            )

        call_vals = {
            "ai_conversation_id": conversation_id,
            "ai_transcript": transcript_plain,
            "ai_agent_id": self.id,
            "summary": call_summary_html or False,
        }

        if call:
            call.write(call_vals)
        else:
            # Twilio routes directly to ElevenLabs — no channel/call exists
            # in Odoo yet.  Create a call log entry so the conversation
            # appears in the Connect call list.
            called_number = _dyn_vars.get("called_number", "")
            call_vals.update({
                "caller": caller_phone or "Unknown",
                "called": called_number or "AI Receptionist",
                "direction": "incoming",
                "status": "completed",
                "partner": partner.id if partner else False,
            })
            call = Call.create(call_vals)

        # Skip CRM lead creation for instructor callers — they're issuing
        # commands, not leads. Check by dojo.instructor.profile.
        is_instructor_caller = False
        if partner and partner.exists():
            is_instructor_caller = bool(
                self.env["dojo.instructor.profile"].sudo().search(
                    [("partner_id", "=", partner.id), ("active", "=", True)],
                    limit=1,
                )
            )

        if is_instructor_caller:
            lead = False
        else:
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

        # Log to ai.action.log if available
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
        """Log to ai.action.log for audit trail."""
        ActionLog = self.env.get("ai.action.log")
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
    # Conversation Initiation Webhook
    # ------------------------------------------------------------------

    def get_conversation_init_data(self, caller_phone="", call_sid="", called_number=""):
        """Build ElevenLabs conversation_initiation_client_data payload.

        Called before the agent speaks its first word. Looks up the caller
        by phone number. Handles three scenarios:
          1. Caller is a dojo.member (student calling directly)
          2. Caller is a guardian whose children are members
          3. Caller is unknown

        Returns a dict matching ElevenLabs' conversation_initiation_client_data schema.
        """
        self.ensure_one()
        from datetime import date as _date

        # ── Caller lookup ────────────────────────────────────────────
        partner = False
        member = False
        is_guardian_call = False
        is_instructor_call = False
        instructor = False
        student_members = self.env["dojo.member"]

        if caller_phone:
            partner = self.env["res.partner"].sudo().get_partner_by_number(caller_phone)
            if partner:
                # Check if caller is a dojo instructor first
                instructor = self.env["dojo.instructor.profile"].sudo().search(
                    [("partner_id", "=", partner.id), ("active", "=", True)],
                    limit=1,
                )
                is_instructor_call = bool(instructor)

                if not is_instructor_call:
                    # Try direct member match
                    member = self.env["dojo.member"].sudo().search(
                        [("partner_id", "=", partner.id), ("active", "=", True)],
                        limit=1,
                    )
                if not is_instructor_call and not member and partner.is_guardian:
                    # Guardian calling — find their household's student members
                    # Household is the parent_id of the guardian partner
                    household = partner.parent_id.filtered("is_household")
                    if household:
                        student_partners = household.child_ids.filtered(
                            lambda p: p.is_student and p.id != partner.id
                        )
                    else:
                        # No household record — look for students that share
                        # the same parent or are directly linked via primary_guardian
                        student_partners = self.env["res.partner"].sudo().search([
                            ("parent_id", "=", partner.id),
                            ("is_student", "=", True),
                        ])
                    if student_partners:
                        student_members = self.env["dojo.member"].sudo().search([
                            ("partner_id", "in", student_partners.ids),
                            ("active", "=", True),
                        ])
                        is_guardian_call = bool(student_members)

        # ── Helper: build per-member summary ─────────────────────────
        def _member_summary(m):
            rank = m.current_rank_id
            last_log = m.attendance_log_ids.sorted("checkin_datetime", reverse=True)[:1]
            last_date_str = ""
            days_str = ""
            if last_log and last_log.checkin_datetime:
                last_date = last_log.checkin_datetime.date()
                last_date_str = last_date.strftime("%B %-d, %Y")
                days_str = str((_date.today() - last_date).days)
            program_name = ""
            if m.active_subscription_id and m.active_subscription_id.plan_id:
                plan = m.active_subscription_id.plan_id
                if hasattr(plan, "program_id") and plan.program_id:
                    program_name = plan.program_id.name
            return {
                "name": m.name.split()[0] if m.name else "",
                "full_name": m.name or "",
                "status": m.membership_state or "unknown",
                "belt_rank": rank.name if rank else "Unranked",
                "total_classes": str(m.total_sessions or 0),
                "last_class_date": last_date_str or "unknown",
                "days_since_class": days_str or "unknown",
                "program": program_name or "General",
            }

        # ── Build dynamic variables ──────────────────────────────────
        dyn = {}

        # Caller identity
        if partner and partner.name:
            dyn["caller_name"] = partner.name.split()[0]
            dyn["caller_full_name"] = partner.name
        else:
            dyn["caller_name"] = ""
            dyn["caller_full_name"] = ""

        dyn["is_guardian"] = "true" if is_guardian_call else "false"
        dyn["is_instructor"] = "true" if is_instructor_call else "false"
        dyn["caller_role"] = "instructor" if is_instructor_call else ("guardian" if is_guardian_call else ("member" if member else "unknown"))

        if is_instructor_call:
            # Instructor calling — personal assistant mode, full access
            dyn["is_member"] = "false"
            dyn["membership_status"] = "Staff"
            dyn["belt_rank"] = ""
            dyn["total_classes"] = ""
            dyn["last_class_date"] = ""
            dyn["days_since_class"] = ""
            dyn["program"] = ""
            dyn["student_name"] = ""
            dyn["student_full_name"] = ""
            dyn["student_status"] = ""
            dyn["student_belt_rank"] = ""
            dyn["student_total_classes"] = ""
            dyn["student_last_class_date"] = ""
            dyn["student_days_since_class"] = ""
            dyn["student_program"] = ""
            dyn["students_summary"] = ""

        elif is_guardian_call:
            # Guardian calling on behalf of children
            dyn["is_member"] = "false"
            dyn["membership_status"] = "Guardian"
            dyn["belt_rank"] = ""
            dyn["total_classes"] = ""
            dyn["last_class_date"] = ""
            dyn["days_since_class"] = ""
            dyn["program"] = ""

            # Build a readable summary of all students in the household
            summaries = [_member_summary(m) for m in student_members]
            # Single child — expose their data directly for easy prompt templating
            if len(summaries) == 1:
                s = summaries[0]
                dyn["student_name"] = s["name"]
                dyn["student_full_name"] = s["full_name"]
                dyn["student_status"] = s["status"].capitalize()
                dyn["student_belt_rank"] = s["belt_rank"]
                dyn["student_total_classes"] = s["total_classes"]
                dyn["student_last_class_date"] = s["last_class_date"]
                dyn["student_days_since_class"] = s["days_since_class"]
                dyn["student_program"] = s["program"]
                dyn["students_summary"] = (
                    f"{s['full_name']} ({s['belt_rank']}, "
                    f"{s['total_classes']} classes, last attended {s['last_class_date']})"
                )
            else:
                # Multiple children — build a comma-separated summary string
                parts = [
                    f"{s['full_name']} ({s['belt_rank']})" for s in summaries
                ]
                dyn["student_name"] = ""
                dyn["student_full_name"] = ""
                dyn["student_status"] = ""
                dyn["student_belt_rank"] = ""
                dyn["student_total_classes"] = ""
                dyn["student_last_class_date"] = ""
                dyn["student_days_since_class"] = ""
                dyn["student_program"] = ""
                dyn["students_summary"] = ", ".join(parts)

        elif member:
            # Student calling directly
            s = _member_summary(member)
            dyn["is_member"] = "true"
            dyn["membership_status"] = dict(
                self.env["dojo.member"]._fields["membership_state"].selection
            ).get(member.membership_state, member.membership_state or "unknown").capitalize()
            dyn["belt_rank"] = s["belt_rank"]
            dyn["total_classes"] = s["total_classes"]
            dyn["last_class_date"] = s["last_class_date"]
            dyn["days_since_class"] = s["days_since_class"]
            dyn["program"] = s["program"]
            dyn["student_name"] = ""
            dyn["student_full_name"] = ""
            dyn["student_status"] = ""
            dyn["student_belt_rank"] = ""
            dyn["student_total_classes"] = ""
            dyn["student_last_class_date"] = ""
            dyn["student_days_since_class"] = ""
            dyn["student_program"] = ""
            dyn["students_summary"] = ""

        else:
            dyn["is_member"] = "false"
            dyn["membership_status"] = "Non-member"
            dyn["belt_rank"] = ""
            dyn["total_classes"] = ""
            dyn["last_class_date"] = ""
            dyn["days_since_class"] = ""
            dyn["program"] = ""
            dyn["student_name"] = ""
            dyn["student_full_name"] = ""
            dyn["student_status"] = ""
            dyn["student_belt_rank"] = ""
            dyn["student_total_classes"] = ""
            dyn["student_last_class_date"] = ""
            dyn["student_days_since_class"] = ""
            dyn["student_program"] = ""
            dyn["students_summary"] = ""

        # ── Personalised first_message ────────────────────────────────
        caller_name = dyn.get("caller_name", "")
        if is_instructor_call and caller_name:
            first_message = (
                f"Hey {caller_name}! What can I do for you?"
            )
        elif is_guardian_call and caller_name:
            students_summary = dyn.get("students_summary", "")
            if students_summary:
                first_message = (
                    f"Hi {caller_name}! I can see you're calling about "
                    f"{students_summary}. How can I help today?"
                )
            else:
                first_message = (
                    f"Hi {caller_name}! How can I help you today?"
                )
        elif member and member.membership_state == "active" and caller_name:
            first_message = (
                f"Hi {caller_name}! Great to hear from you. How can I help you today?"
            )
        elif member and member.membership_state == "trial" and caller_name:
            first_message = (
                f"Hi {caller_name}! Welcome — glad you're trying us out. How can I help?"
            )
        elif caller_name:
            first_message = f"Hi {caller_name}! Thanks for calling. How can I help you today?"
        else:
            first_message = "Thanks for calling! How can I help you today?"

        # Include caller_phone in dynamic_variables so it's available in the
        # post-call webhook under conversation_initiation_client_data.dynamic_variables
        dyn["caller_phone"] = caller_phone or ""
        dyn["call_sid"] = call_sid or ""
        dyn["called_number"] = called_number or ""

        return {
            "type": "conversation_initiation_client_data",
            "dynamic_variables": dyn,
            "conversation_config_override": {
                "agent": {
                    "first_message": first_message,
                }
            },
        }

    # ------------------------------------------------------------------
    # Webhook signature validation
    # ------------------------------------------------------------------

    def verify_webhook_signature(self, payload_body, signature_header, signing_secret=None):
        """Validate ElevenLabs post-call webhook signature.

        ElevenLabs signs webhooks using the format:
            X-ElevenLabs-Signature: t=<timestamp>,v0=<hmac_sha256_hex>

        The signed payload is: "<timestamp>,<raw_body>"
        """
        self.ensure_one()
        secret = signing_secret or self.elevenlabs_webhook_secret
        if not secret:
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
            secret.encode(),
            signed_payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, v0)
