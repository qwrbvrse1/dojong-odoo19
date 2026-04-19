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

import json
import logging
import secrets

import requests
from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# ElevenLabs STT supported language codes (ISO 639-1)
_SUPPORTED_STT_LANGS = [
    ("en", "English"),
    ("es", "Spanish"),
    ("fr", "French"),
    ("de", "German"),
    ("pt", "Portuguese"),
    ("it", "Italian"),
    ("ko", "Korean"),
    ("ja", "Japanese"),
    ("zh", "Chinese"),
    ("ar", "Arabic"),
    ("hi", "Hindi"),
    ("ru", "Russian"),
    ("nl", "Dutch"),
    ("pl", "Polish"),
    ("tr", "Turkish"),
    ("vi", "Vietnamese"),
    ("th", "Thai"),
    ("id", "Indonesian"),
    ("tl", "Filipino"),
]

# Human-readable names for building translation labels
_LANG_NAMES = {code: name for code, name in _SUPPORTED_STT_LANGS}


def _odoo_lang_to_stt(odoo_lang):
    """Convert Odoo locale code (e.g. 'ko_KR') to ISO 639-1 (e.g. 'ko').

    Returns 'en' if the language is unsupported or not set.
    """
    if not odoo_lang:
        return "en"
    iso = odoo_lang.split("_")[0].lower()
    supported = {code for code, _ in _SUPPORTED_STT_LANGS}
    return iso if iso in supported else "en"


class AiWalkieTalkie(models.Model):
    _name = "ai.walkie.talkie"
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

    # ── Language / STT ────────────────────────────────────────────────────
    stt_language = fields.Selection(
        selection=_SUPPORTED_STT_LANGS,
        string="STT Language",
        default="en",
        help="Language used for speech-to-text on the standalone URL. "
             "Backend users use their Odoo language preference instead.",
    )

    # ── Discuss integration ────────────────────────────────────────────────
    discuss_post_as_id = fields.Many2one(
        "res.partner",
        string="Post As",
        ondelete="set null",
        help="Voice messages on the standalone URL will be posted to Discuss as this contact. "
             "If blank, defaults to OdooBot. Backend users always post as themselves.",
    )
    elder_discuss_channel_id = fields.Many2one(
        "discuss.channel",
        string="Elder Discuss Channel",
        ondelete="set null",
        help="Discuss channel where Elder Beta voice messages and AI responses are posted.",
    )
    channel_mapping_ids = fields.One2many(
        "ai.walkie.channel.mapping",
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
            "default": "ai_assistant.walkie_talkie",
            "channel_beta": "ai_assistant.walkie_channel",
            "elder_beta": "ai_assistant.walkie_elder",
        }
        tag = tag_map.get(self.mode, "ai_assistant.walkie_talkie")
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

    def get_stt_language(self, user=None):
        """Return the ISO 639-1 language code to use for STT.

        - If a logged-in user is given, derive from their Odoo language preference.
        - Otherwise fall back to this station's ``stt_language`` field.
        """
        if user and user.lang:
            return _odoo_lang_to_stt(user.lang)
        return self.stt_language or "en"

    def _translate_text(self, text, target_lang_code):
        """Translate *text* into *target_lang_code* (ISO 639-1) via OpenAI.

        Returns the translated string, or the original text on failure.
        """
        target_name = _LANG_NAMES.get(target_lang_code, target_lang_code)
        api_key = (
            self.env["ir.config_parameter"].sudo().get_str("openai.api_key")
            or self.env["ir.config_parameter"].sudo().get_str("elevenlabs_connector.openai_api_key")
        )
        if not api_key:
            _logger.warning("OpenAI API key not configured — skipping translation")
            return text

        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"You are a translator. Translate the following text into {target_name}. "
                        "Return ONLY the translated text, nothing else."
                    ),
                },
                {"role": "user", "content": text},
            ],
            "temperature": 0.3,
            "max_tokens": 2000,
        }

        try:
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                timeout=30,
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("choices"):
                return result["choices"][0]["message"]["content"].strip()
        except Exception:
            _logger.warning("Translation to %s failed, using original text", target_lang_code, exc_info=True)
        return text

    def _get_channel_member_languages(self, channel_type=None):
        """Return a set of unique ISO 639-1 language codes for members of the mapped Discuss channel."""
        discuss_channel = self._resolve_discuss_channel(channel_type)
        if not discuss_channel:
            return set()
        langs = set()
        for partner in discuss_channel.channel_partner_ids:
            lang_code = _odoo_lang_to_stt(partner.lang)
            langs.add(lang_code)
        return langs or {"en"}

    def _build_translated_body(self, text, channel_type=None, source_lang="en"):
        """Build a plain-text body with translations for each unique language in the channel.

        If the channel has only one language matching source_lang, returns plain text.
        Otherwise, returns the original text plus a translation block for each other language.
        """
        member_langs = self._get_channel_member_languages(channel_type)
        # Remove source language — no need to translate to itself
        other_langs = member_langs - {source_lang}
        if not other_langs:
            return text

        from markupsafe import escape
        source_name = _LANG_NAMES.get(source_lang, source_lang)
        parts = [f"[{source_name}]<br/>{escape(text)}"]
        for lang_code in sorted(other_langs):
            translated = self._translate_text(text, lang_code)
            lang_name = _LANG_NAMES.get(lang_code, lang_code)
            parts.append(f"[{lang_name}]<br/>{escape(translated)}")

        return Markup("<br/><br/>".join(parts))

    def _resolve_discuss_channel(self, channel_type=None):
        """Return the ``discuss.channel`` record for the given AI channel, or False."""
        self.ensure_one()
        if self.mode in ("channel_beta", "elder_beta"):
            mapping = self.channel_mapping_ids.filtered(
                lambda m: m.channel_type == (channel_type or "all")
            )
            return mapping.discuss_channel_id if mapping else self.env["discuss.channel"]
        return self.env["discuss.channel"]

    def post_voice_to_discuss(self, audio_bytes, transcription, channel_type=None, author_id=None, source_lang="en"):
        """Post the user's voice recording + transcription to the mapped Discuss channel.

        :param bytes audio_bytes: raw WebM/Opus audio
        :param str transcription: STT transcription text
        :param str channel_type: AI channel key (e.g. 'attendance'); elder mode ignores this
        :param int author_id: res.partner id of the message author (logged-in user)
        :param str source_lang: ISO 639-1 code of the speaker's language
        :returns: mail.message record or False
        """
        self.ensure_one()
        discuss_channel = self._resolve_discuss_channel(channel_type)
        if not discuss_channel:
            return False
        try:
            body = self._build_translated_body(
                transcription or "", channel_type=channel_type, source_lang=source_lang,
            )
            msg = discuss_channel.sudo().message_post(
                body=body,
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

    def post_ai_response_to_discuss(self, response_text, channel_type=None, source_lang="en"):
        """Post the AI assistant's text response to the mapped Discuss channel.

        Always authored by OdooBot to distinguish AI messages from human ones.

        :param str response_text: AI response text
        :param str channel_type: AI channel key
        :param str source_lang: ISO 639-1 code of the AI response language (usually same as user)
        :returns: mail.message record or False
        """
        self.ensure_one()
        if not response_text:
            return False
        discuss_channel = self._resolve_discuss_channel(channel_type)
        if not discuss_channel:
            return False
        try:
            body = self._build_translated_body(
                response_text, channel_type=channel_type, source_lang=source_lang,
            )
            odoobot = self.env.ref("base.partner_root", raise_if_not_found=False)
            msg = discuss_channel.sudo().message_post(
                body=body,
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
