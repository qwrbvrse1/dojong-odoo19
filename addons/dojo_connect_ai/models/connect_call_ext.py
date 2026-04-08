# -*- coding: utf-8 -*-

from odoo import fields, models


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
