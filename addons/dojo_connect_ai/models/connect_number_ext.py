# -*- coding: utf-8 -*-
"""Kept for database compatibility — fields already exist in production.

Twilio calls are now routed directly to ElevenLabs (configured in the
ElevenLabs dashboard).  Odoo no longer renders TwiML or routes calls
through ``connect.number``.  The field definitions below prevent
orphaned-column issues on upgrade.
"""

from odoo import fields, models


class ConnectNumber(models.Model):
    _inherit = "connect.number"

    destination = fields.Selection(
        selection_add=[("ai_agent", "AI Agent")],
        ondelete={"ai_agent": "set null"},
    )
    ai_agent_id = fields.Many2one(
        "connect.ai.agent",
        string="AI Agent",
        ondelete="set null",
    )
