# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    connect_ai_enabled = fields.Boolean(
        string="AI Receptionist Enabled",
        config_parameter="dojo_connect_ai.enabled",
        help="Enable the AI voice agent (Kai) for incoming calls.",
    )
    connect_ai_auto_lead = fields.Boolean(
        string="Auto-Create Lead After AI Call",
        config_parameter="dojo_connect_ai.auto_lead",
        default=True,
        help="Automatically create a CRM lead after every AI conversation.",
    )
    connect_ai_missed_call_lead = fields.Boolean(
        string="Create Lead on Missed Call",
        config_parameter="dojo_connect_ai.missed_call_lead",
        default=True,
        help="Auto-create a CRM lead when an incoming call to an AI number is missed.",
    )
