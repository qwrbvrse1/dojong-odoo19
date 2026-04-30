"""Link transactional templates (mail.template / sms.template) to a Marketing Card.

When set, the CRM Templates drawer surfaces the linked card and lets the user
preview / open the campaign. Renderers can also inject the card URL into the
template body when sending.
"""
import logging

from odoo import fields, models
from markupsafe import Markup

_logger = logging.getLogger(__name__)


class MailTemplateCard(models.Model):
    _inherit = "mail.template"

    card_campaign_id = fields.Many2one(
        "card.campaign",
        string="Marketing Card",
        domain="[('res_model', '=', model)]",
        ondelete="set null",
        help="Optional Marketing Card campaign embedded with this email template.",
    )

    def _render_field(self, field, res_ids, **kwargs):
        results = super()._render_field(field, res_ids, **kwargs)
        # Only inject for HTML body field and when a card is linked
        if field != "body_html" or not self.card_campaign_id or not res_ids:
            return results
        try:
            block_per_res = self._dojo_get_card_blocks(res_ids)
        except Exception as e:
            _logger.warning(
                "Marketing card injection failed for template %s: %s", self.id, e
            )
            return results
        for res_id in res_ids:
            html_block = block_per_res.get(res_id)
            if not html_block:
                continue
            current = results.get(res_id) or ""
            results[res_id] = (current or "") + html_block
        return results

    def _dojo_get_card_blocks(self, res_ids):
        """Return a dict {res_id: html} with the personalised card snippet."""
        self.ensure_one()
        camp = self.card_campaign_id.sudo()
        if not camp:
            return {}
        # Make sure cards exist for these res_ids and are rendered
        try:
            camp._update_cards([("id", "in", list(res_ids))])
        except Exception as e:
            _logger.warning(
                "card.campaign._update_cards failed for campaign %s: %s",
                camp.id, e,
            )
            return {}
        cards = self.env["card.card"].sudo().search([
            ("campaign_id", "=", camp.id),
            ("res_id", "in", list(res_ids)),
        ])
        out = {}
        accent = "#5D8DA8"
        for card in cards:
            if not card.image:
                continue
            try:
                img_url = card._get_card_url()
                redirect_url = card._get_redirect_url()
            except Exception:
                continue
            title = (camp.name or "").strip() or "Personal Card"
            out[card.res_id] = Markup(
                '<div style="margin:18px 0 10px 0;font-size:13px;color:#6b7280;'
                'text-transform:uppercase;letter-spacing:0.04em;font-weight:600;">'
                'A little something for you</div>'
                '<table cellpadding="0" cellspacing="0" border="0" width="100%" '
                'style="border-collapse:separate;margin-bottom:10px;">'
                '<tr><td style="padding:6px;vertical-align:top;">'
                '<table cellpadding="0" cellspacing="0" border="0" width="100%" '
                'style="background:#f8fafc;border:1px solid #e5e7eb;border-radius:10px;">'
                '<tr><td style="padding:14px 16px;">'
                f'<div style="font-size:13px;font-weight:600;color:#111827;'
                f'margin-bottom:10px;">{title}</div>'
                f'<a href="{redirect_url}" target="_blank">'
                f'<img src="{img_url}" alt="{title}" '
                f'style="display:block;width:100%;max-width:480px;height:auto;'
                f'border-radius:8px;border:1px solid #e5e7eb;"/>'
                '</a>'
                '<table cellpadding="0" cellspacing="0" border="0" '
                'style="margin-top:10px;border-collapse:separate;">'
                f'<tr><td bgcolor="{accent}" '
                f'style="background-color:{accent};border-radius:8px;padding:8px 14px;">'
                f'<a href="{redirect_url}" target="_blank" '
                f'style="color:#ffffff;text-decoration:none;font-size:13px;'
                f'font-weight:600;display:inline-block;">'
                f'Open &rarr;</a>'
                '</td></tr></table>'
                '</td></tr></table></td></tr></table>'
            )
        return out


class SmsTemplateCard(models.Model):
    _inherit = "sms.template"

    card_campaign_id = fields.Many2one(
        "card.campaign",
        string="Marketing Card",
        domain="[('res_model', '=', model)]",
        ondelete="set null",
        help="Optional Marketing Card campaign linked with this SMS template "
             "(its short URL can be inserted into the body).",
    )

    def _render_field(self, field, res_ids, **kwargs):
        results = super()._render_field(field, res_ids, **kwargs)
        if field != "body" or not self.card_campaign_id or not res_ids:
            return results
        try:
            url_per_res = self._dojo_get_card_urls(res_ids)
        except Exception as e:
            _logger.warning(
                "Marketing card URL injection failed for SMS template %s: %s",
                self.id, e,
            )
            return results
        for res_id in res_ids:
            url = url_per_res.get(res_id)
            if not url:
                continue
            current = results.get(res_id) or ""
            # Only append if URL not already in the body
            if url not in current:
                results[res_id] = (current.rstrip() + " " + url).strip()
        return results

    def _dojo_get_card_urls(self, res_ids):
        self.ensure_one()
        camp = self.card_campaign_id.sudo()
        if not camp:
            return {}
        try:
            camp._update_cards([("id", "in", list(res_ids))])
        except Exception as e:
            _logger.warning(
                "card.campaign._update_cards failed for campaign %s: %s",
                camp.id, e,
            )
            return {}
        cards = self.env["card.card"].sudo().search([
            ("campaign_id", "=", camp.id),
            ("res_id", "in", list(res_ids)),
        ])
        out = {}
        for card in cards:
            try:
                out[card.res_id] = card._get_redirect_url()
            except Exception:
                continue
        return out
