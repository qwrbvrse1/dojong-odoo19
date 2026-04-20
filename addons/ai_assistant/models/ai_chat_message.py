# -*- coding: utf-8 -*-
"""
AI Chat Message — Lightweight conversation history for multi-turn AI sessions.

Each record represents a single message (user or assistant) within a
chat session identified by ``chat_session_id``.  The n8n router writes
here on every turn so that subsequent calls can retrieve context.
"""

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AiChatMessage(models.Model):
    _name = "ai.chat.message"
    _description = "AI Chat Message"
    _order = "timestamp asc, id asc"

    chat_session_id = fields.Char(
        string="Chat Session ID",
        required=True,
        index=True,
        help="Client-supplied conversation session identifier (same across turns)",
    )
    role = fields.Selection(
        [
            ("user", "User"),
            ("assistant", "Assistant"),
        ],
        string="Role",
        required=True,
    )
    content = fields.Text(
        string="Content",
        required=True,
    )
    timestamp = fields.Datetime(
        string="Timestamp",
        default=fields.Datetime.now,
        index=True,
    )
