# -*- coding: utf-8 -*-
"""
Dojo Walkie-Talkie — persistent named instances of the AI Walkie-Talkie.

Each record represents one physical station (e.g. "Front Desk", "Mat 1").
Admins create instances in the backend; instructors launch them via the
"Launch" button which opens the Walkie-Talkie client action with instance
metadata injected through the action context.

Each instance also has a standalone public URL: /walkie/<token>
accessible outside the Odoo backend, similar to the kiosk.
"""

import secrets

from odoo import api, fields, models
from odoo.exceptions import UserError


class DojoWalkieTalkie(models.Model):
    _name = "dojo.walkie.talkie"
    _description = "AI Walkie-Talkie Instance"
    _order = "name"

    name = fields.Char(string="Name", required=True)
    description = fields.Text(string="Description")
    active = fields.Boolean(default=True)
    last_used = fields.Datetime(string="Last Used", readonly=True)
    # PROTOTYPE: mode selector — default keeps original behaviour untouched
    mode = fields.Selection(
        selection=[
            ("default", "Default"),
            ("channel_beta", "Channel Beta (Prototype)"),
            ("elder_beta", "Elder Beta (Prototype)"),
        ],
        string="Mode",
        default="default",
        required=True,
    )
    walkie_token = fields.Char(
        string="Standalone Token",
        readonly=True,
        copy=False,
        help="Unique token used in the standalone /walkie/<token> URL.",
    )
    walkie_pin = fields.Char(
        string="Access PIN",
        copy=False,
        help="PIN required to access this walkie-talkie on the standalone URL (4–8 digits). Set by admin; not shown to instructors.",
    )
    walkie_url = fields.Char(
        string="Standalone URL",
        compute="_compute_walkie_url",
        store=False,
    )

    @api.depends("walkie_token")
    def _compute_walkie_url(self):
        base = self.env["ir.config_parameter"].sudo().get_str("web.base.url") or ""
        for rec in self:
            if rec.walkie_token:
                rec.walkie_url = f"{base}/walkie/{rec.walkie_token}"
            else:
                rec.walkie_url = ""

    def action_generate_token(self):
        """Generate (or regenerate) the standalone URL token for this instance."""
        for rec in self:
            rec.walkie_token = secrets.token_urlsafe(24)
        return True

    def action_launch(self):
        """Open the standalone walkie-talkie URL in a new tab."""
        self.ensure_one()
        if not self.walkie_token:
            self.walkie_token = secrets.token_urlsafe(24)
        self.sudo().write({"last_used": fields.Datetime.now()})
        return {
            "type": "ir.actions.act_url",
            "url": f"/walkie/{self.walkie_token}",
            "target": "new",
        }

    def action_launch_backend(self):
        """
        Open the walkie-talkie as an Odoo backend client action, routed by mode.
        PROTOTYPE: channel_beta and elder_beta use their own client action tags.
        """
        self.ensure_one()
        self.sudo().write({"last_used": fields.Datetime.now()})
        tag_map = {
            "default": "dojo_assistant.walkie_talkie",
            "channel_beta": "dojo_assistant.walkie_channel",
            "elder_beta": "dojo_assistant.walkie_elder",
        }
        tag = tag_map.get(self.mode, "dojo_assistant.walkie_talkie")
        return {
            "type": "ir.actions.client",
            "tag": tag,
            "name": self.name,
            "context": {
                "walkie_id": self.id,
                "walkie_name": self.name,
                "walkie_mode": self.mode,
            },
        }
