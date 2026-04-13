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

import logging
import secrets

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


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

    # ── Discuss integration ────────────────────────────────────────────────
    elder_discuss_channel_id = fields.Many2one(
        "discuss.channel",
        string="Elder Discuss Channel",
        ondelete="set null",
        help="Discuss channel where Elder Beta voice messages and AI responses are posted.",
    )
    channel_mapping_ids = fields.One2many(
        "dojo.walkie.channel.mapping",
        "walkie_talkie_id",
        string="Channel → Discuss Mappings",
        help="Map each AI channel to a Discuss channel for automatic voice message posting.",
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

    # ═══════════════════════════════════════════════════════════════════════
    # Discuss integration helpers
    # ═══════════════════════════════════════════════════════════════════════

    def _resolve_discuss_channel(self, channel_type=None):
        """Return the ``discuss.channel`` record for the given AI channel, or False."""
        self.ensure_one()
        if self.mode == "elder_beta":
            return self.elder_discuss_channel_id or self.env["discuss.channel"]
        if self.mode == "channel_beta":
            mapping = self.channel_mapping_ids.filtered(
                lambda m: m.channel_type == (channel_type or "all")
            )
            return mapping.discuss_channel_id if mapping else self.env["discuss.channel"]
        return self.env["discuss.channel"]

    def post_voice_to_discuss(self, audio_bytes, transcription, channel_type=None, author_id=None):
        """Post the user's voice recording + transcription to the mapped Discuss channel.

        :param bytes audio_bytes: raw WebM/Opus audio
        :param str transcription: STT transcription text
        :param str channel_type: AI channel key (e.g. 'attendance'); elder mode ignores this
        :param int author_id: res.partner id of the message author (logged-in user)
        :returns: mail.message record or False
        """
        self.ensure_one()
        discuss_channel = self._resolve_discuss_channel(channel_type)
        if not discuss_channel:
            return False
        try:
            msg = discuss_channel.sudo().message_post(
                body=transcription or "",
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
                author_id=author_id,
                attachments=[("walkie.webm", audio_bytes, {"voice": True})],
            )
            return msg
        except Exception:
            _logger.warning(
                "Failed to post voice message to Discuss channel %s (walkie %s)",
                discuss_channel.id, self.id, exc_info=True,
            )
            return False

    def post_ai_response_to_discuss(self, response_text, channel_type=None):
        """Post the AI assistant's text response to the mapped Discuss channel.

        Always authored by OdooBot to distinguish AI messages from human ones.

        :param str response_text: AI response text
        :param str channel_type: AI channel key
        :returns: mail.message record or False
        """
        self.ensure_one()
        if not response_text:
            return False
        discuss_channel = self._resolve_discuss_channel(channel_type)
        if not discuss_channel:
            return False
        try:
            odoobot = self.env.ref("base.partner_root", raise_if_not_found=False)
            msg = discuss_channel.sudo().message_post(
                body=response_text,
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
                author_id=odoobot.id if odoobot else None,
            )
            return msg
        except Exception:
            _logger.warning(
                "Failed to post AI response to Discuss channel %s (walkie %s)",
                discuss_channel.id, self.id, exc_info=True,
            )
            return False
