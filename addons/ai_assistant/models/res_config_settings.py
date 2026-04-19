# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ai_context_window_turns = fields.Integer(
        string="Context Window (turns)",
        config_parameter="ai_assistant.context_window_turns",
        default=10,
        help=(
            "Number of previous conversation turns sent to the AI with each request. "
            "1 turn = one user message + one AI reply. Range: 1–50. Default: 10."
        ),
    )

    ai_api_key = fields.Char(
        string="API Key (n8n / external)",
        config_parameter="ai_assistant.api_key",
        help=(
            "Secret key for the /api/v1/ai/* endpoints. "
            "External callers (n8n, MCP) must send this in the X-Api-Key header."
        ),
    )
