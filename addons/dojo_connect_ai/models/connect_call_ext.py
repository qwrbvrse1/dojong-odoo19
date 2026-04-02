# -*- coding: utf-8 -*-

import logging

from odoo import fields, models, api

_logger = logging.getLogger(__name__)

MISSED_STATUSES = {"no-answer", "busy", "failed", "canceled"}


class ConnectCall(models.Model):
    _inherit = "connect.call"

    # ── AI conversation fields ───────────────────────────────────────
    ai_conversation_id = fields.Char(
        string="AI Conversation ID",
        readonly=True,
        help="ElevenLabs conversation identifier.",
    )
    ai_transcript = fields.Text(
        string="AI Transcript",
        readonly=True,
    )
    ai_lead_id = fields.Many2one(
        "crm.lead",
        string="CRM Lead",
        ondelete="set null",
        readonly=True,
    )
    ai_agent_id = fields.Many2one(
        "connect.ai.agent",
        string="AI Agent",
        ondelete="set null",
        readonly=True,
    )

    @api.model
    def on_call_status(self, params):
        """Extend to handle missed calls for AI-routed numbers."""
        res = super().on_call_status(params)

        call_status = params.get("CallStatus", "")
        if call_status not in MISSED_STATUSES:
            return res

        direction = params.get("Direction", "")
        if direction != "inbound" and not (
            # Connect module uses 'inbound' for DID calls;
            # also check if caller has no PBX user (incoming external)
            not self.env["connect.user"].sudo().get_user_by_uri(
                params.get("From", "")
            )
        ):
            return res

        # Check if the called number is routed to an AI agent
        called_number = params.get("Called", "") or params.get("To", "")
        number_rec = self.env["connect.number"].sudo().search(
            [("phone_number", "=", called_number)], limit=1
        )
        if not number_rec or number_rec.destination != "ai_agent" or not number_rec.ai_agent_id:
            return res

        # Check if missed-call lead creation is enabled
        enabled = self.env["ir.config_parameter"].sudo().get_param(
            "dojo_connect_ai.missed_call_lead", "True"
        )
        if enabled.lower() not in ("1", "true"):
            return res

        caller_phone = params.get("From", "")
        if not caller_phone:
            return res

        # Find the call record we just created/updated
        call_sid = params.get("CallSid", "")
        call = False
        if call_sid:
            channel = self.env["connect.channel"].sudo().search(
                [("sid", "=", call_sid)], limit=1
            )
            if channel and channel.call:
                call = channel.call

        number_rec.ai_agent_id.sudo().create_missed_call_lead(
            caller_phone, call=call
        )

        return res
