# -*- coding: utf-8 -*-

from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    ai_agent_id = fields.Many2one(
        "connect.ai.agent",
        string="AI Agent",
        ondelete="set null",
        readonly=True,
        help="The AI agent that created or handled this lead.",
    )
