# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ai_context_window_turns = fields.Integer(
        string="Context Window (turns)",
        config_parameter="dojo_assistant.context_window_turns",
        default=10,
        help=(
            "Number of previous conversation turns sent to the AI with each request. "
            "1 turn = one user message + one AI reply. Range: 1–50. Default: 10."
        ),
    )
