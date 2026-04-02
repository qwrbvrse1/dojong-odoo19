# -*- coding: utf-8 -*-

import json
import logging

from odoo import fields, models, api
from .connect_ai_agent import _logger  # reuse module logger


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

    @api.model
    def route_call(self, request):
        """Extend to handle AI agent destination."""
        number = self.search([("phone_number", "=", request.get("Called", ""))])
        if number and number.destination == "ai_agent" and number.ai_agent_id:
            # Create call tracking record (same as parent)
            self.env["connect.call"].sudo().on_call_status(request)
            return number.ai_agent_id.render_twiml(request)
        return super().route_call(request)

    def write(self, vals):
        if vals.get("destination") == "ai_agent":
            vals.setdefault("user", False)
            vals.setdefault("callflow", False)
            vals.setdefault("twiml", False)
        elif "destination" in vals and vals["destination"] != "ai_agent":
            vals.setdefault("ai_agent_id", False)
        return super().write(vals)
