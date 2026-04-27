from datetime import timedelta
import re
import secrets

from werkzeug.security import check_password_hash, generate_password_hash

from odoo import api, fields, models
from odoo.exceptions import ValidationError


_PIN_HASH_PREFIXES = ("pbkdf2:", "scrypt:")


def _looks_like_password_hash(value):
    return bool(value) and value.startswith(_PIN_HASH_PREFIXES) and "$" in value


class DojoKioskConfig(models.Model):
    _name = "dojo.kiosk.config"
    _description = "Dojang Kiosk Configuration"
    _order = "name"

    name = fields.Char(string="Kiosk Name", required=True)
    pin_code = fields.Char(
        string="Instructor PIN",
        required=True,
        help="Exactly 6 digits used to unlock Instructor Mode on this kiosk.",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        index=True,
    )
    active = fields.Boolean(default=True)

    # ── Token-based device auth ────────────────────────────────────────
    kiosk_token = fields.Char(
        string="Kiosk Token",
        readonly=True,
        copy=False,
        index=True,
        help="Unguessable URL token. Share the Kiosk URL with the tablet operator.",
    )
    kiosk_url = fields.Char(
        string="Kiosk URL",
        compute="_compute_kiosk_url",
        help="Open this URL on the kiosk tablet.",
    )

    # ── Theming & announcements ────────────────────────────────────────
    theme_mode = fields.Selection(
        [("dark", "Dark"), ("light", "Light")],
        string="Theme",
        default="dark",
    )
    view_mode = fields.Selection(
        [("search_only", "Search Only"), ("both", "Barcode + Search")],
        string="Student Check-in View",
        default="search_only",
        help="Determines the check-in interface shown to students.",
    )
    show_title = fields.Boolean(
        string="Show Dojang Title",
        default=True,
        help="Show the 'Dojang' title in the kiosk header.",
    )
    announcement_ids = fields.One2many(
        "dojo.kiosk.announcement",
        "config_id",
        string="Idle Screen Announcements",
    )

    # ── Lifecycle ─────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("kiosk_token"):
                vals["kiosk_token"] = secrets.token_urlsafe(32)
            self._prepare_pin_vals(vals)
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)
        self._prepare_pin_vals(vals)
        return super().write(vals)

    def action_regenerate_token(self):
        """Regenerate the kiosk token (invalidates any open tablet sessions)."""
        for cfg in self:
            cfg.kiosk_token = secrets.token_urlsafe(32)

    def action_open_kiosk_url(self):
        """Open this kiosk's URL in a new browser tab."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": self.kiosk_url,
            "target": "new",
        }

    def _compute_kiosk_url(self):
        base = self.env["ir.config_parameter"].sudo().get_str("web.base.url") or ""
        for cfg in self:
            if cfg.kiosk_token:
                cfg.kiosk_url = f"{base}/kiosk/{cfg.kiosk_token}"
            else:
                cfg.kiosk_url = ""

    def _prepare_pin_vals(self, vals):
        pin = (vals.get("pin_code") or "").strip()
        if not pin:
            return vals
        vals["pin_code"] = pin if _looks_like_password_hash(pin) else generate_password_hash(
            pin,
            method="pbkdf2:sha256",
        )
        return vals

    def _verify_pin_value(self, raw_pin):
        self.ensure_one()
        raw_pin = (raw_pin or "").strip()
        stored = self.pin_code or ""
        if not raw_pin or not stored:
            return False
        if _looks_like_password_hash(stored):
            try:
                return check_password_hash(stored, raw_pin)
            except ValueError:
                return False
        if stored == raw_pin:
            self.sudo().write({"pin_code": raw_pin})
            return True
        return False

    def _get_or_create_pin_attempt(self):
        self.ensure_one()
        Attempt = self.env["dojo.kiosk.pin.attempt"].sudo()
        attempt = Attempt.search([("config_id", "=", self.id)], limit=1)
        if attempt:
            return attempt
        try:
            return Attempt.create({"config_id": self.id})
        except Exception:
            return Attempt.search([("config_id", "=", self.id)], limit=1)

    def _get_pin_lock_state(self):
        self.ensure_one()
        attempt = self._get_or_create_pin_attempt()
        now = fields.Datetime.now()
        if attempt.locked_until and now < attempt.locked_until:
            remaining = int((attempt.locked_until - now).total_seconds() / 60) + 1
            return {"locked": True, "retry_in_minutes": remaining}
        return {"locked": False}

    def _clear_pin_attempts(self):
        for kiosk in self:
            kiosk._get_or_create_pin_attempt().sudo().write({
                "failed_attempts": 0,
                "locked_until": False,
                "last_attempt_at": fields.Datetime.now(),
            })

    def _register_pin_failure(self, max_attempts, lockout_minutes):
        self.ensure_one()
        attempt = self._get_or_create_pin_attempt()
        failed_attempts = (attempt.failed_attempts or 0) + 1
        vals = {
            "failed_attempts": failed_attempts,
            "last_attempt_at": fields.Datetime.now(),
            "locked_until": False,
        }
        if failed_attempts >= max_attempts:
            vals.update({
                "failed_attempts": 0,
                "locked_until": fields.Datetime.now() + timedelta(minutes=lockout_minutes),
            })
            attempt.sudo().write(vals)
            return {"locked": True, "retry_in_minutes": lockout_minutes}
        attempt.sudo().write(vals)
        return {"locked": False, "remaining_tries": max_attempts - failed_attempts}

    @api.constrains("pin_code")
    def _check_pin_code(self):
        for kiosk in self:
            if _looks_like_password_hash(kiosk.pin_code):
                continue
            if not re.fullmatch(r"\d{6}", kiosk.pin_code or ""):
                raise ValidationError(
                    "Instructor PIN must be exactly 6 digits (numbers only)."
                )
