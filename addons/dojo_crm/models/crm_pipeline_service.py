"""
crm_pipeline_service.py
=======================
AbstractModel providing all JSON-serialisable read/write helpers
for the custom CRM Pipeline Board OWL client action.

Every method is decorated @api.model so it can be called via
orm.call('crm.pipeline.service', 'method_name', [...args]).
"""
import logging
from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools import html2plaintext

_logger = logging.getLogger(__name__)


def _html_to_plain(value):
    """Convert lead.description HTML to plain text for textarea round-trip."""
    if not value:
        return ""
    return (html2plaintext(value) or "").strip()


def _render_inline_for_lead(env, body, lead_id):
    """Render `{{ object.x }}` Inline Template tokens against a single crm.lead.

    Returns the rendered string, or the original body unchanged on failure / no
    tokens. Used both at message-display time (defensive) and at message-post
    time (so stored bodies are already resolved).
    """
    if not body or "{{" not in body:
        return body or ""
    try:
        rendered = env["mail.render.mixin"].sudo()._render_template(
            body,
            "crm.lead",
            [lead_id],
            engine="inline_template",
            post_process=False,
        )
        return rendered.get(lead_id, body) or body
    except Exception as e:
        _logger.warning(
            "Inline-template render failed for lead %s: %s", lead_id, e
        )
        return body

# Stage order must match data/crm_stage.xml
STAGE_ORDER = [
    "New",
    "Qualified",
    "Trial Booked",
    "Trial-in-progress",
    "Evaluation",
    "Won",
]

# Filter-chip → ORM domain fragment
_CHIP_DOMAINS = {
    "high_score":       [("dojo_lead_score", ">=", 60)],
    "trial_attended":   [("trial_attended", "=", True)],
    "no_show":          [("no_show", "=", True)],
    "converted":        [("is_converted", "=", True)],
    "has_booking_link": [("trial_booking_token", "!=", False)],
}


def _lead_dict(lead):
    """Return a compact JSON-serialisable dict for a single crm.lead record."""
    return {
        "id":               lead.id,
        "name":             lead.name or "",
        "contact_name":     lead.contact_name or "",
        "partner_name":     lead.partner_name or "",
        "email_from":       lead.email_from or "",
        "phone":            lead.phone or "",
        "stage_id":         lead.stage_id.id,
        "stage_name":       lead.stage_id.name or "",
        "user_id":          lead.user_id.id if lead.user_id else False,
        "user_name":        lead.user_id.name if lead.user_id else "",
        "tag_ids":          lead.tag_ids.ids,
        "tag_names":        lead.tag_ids.mapped("name"),
        "dojo_lead_score":  lead.dojo_lead_score,
        "trial_attended":   lead.trial_attended,
        "no_show":          lead.no_show,
        "is_converted":     lead.is_converted,
        "trial_booking_token": lead.trial_booking_token or "",
        "trial_booking_url":   lead.trial_booking_url or "",
        "trial_manage_url":    lead.trial_manage_url or "",
        "booking_link_clicked": lead.booking_link_clicked,
        "trial_session_id":   lead.trial_session_id.id if lead.trial_session_id else False,
        "trial_session_name": lead.trial_session_id.name if lead.trial_session_id else "",
        "trial_session_dt":   (
            str(lead.trial_session_id.start_datetime)
            if lead.trial_session_id and lead.trial_session_id.start_datetime
            else ""
        ),
        "dojo_member_id":  lead.dojo_member_id.id if lead.dojo_member_id else False,
        "offer_sent_date": str(lead.offer_sent_date) if lead.offer_sent_date else "",
        "last_engagement_date": (
            str(lead.last_engagement_date) if lead.last_engagement_date else ""
        ),
        "ai_summary": lead.ai_summary or "",
        "description": _html_to_plain(lead.description),
        "active": lead.active,
        "priority": lead.priority or "0",
        "date_deadline": str(lead.date_deadline) if lead.date_deadline else "",
        "partner_id": lead.partner_id.id if lead.partner_id else False,
        "partner_avatar": (
            "/web/image/res.partner/%d/avatar_128" % lead.partner_id.id
            if lead.partner_id
            else "/web/static/img/placeholder.png"
        ),
    }


class CrmPipelineService(models.AbstractModel):
    """Read/write service for the custom CRM pipeline OWL board."""

    _name = "crm.pipeline.service"
    _description = "CRM Pipeline Board Service"

    # ------------------------------------------------------------------
    # Board bootstrap — called once on mount
    # ------------------------------------------------------------------

    @api.model
    def get_board_data(self, active_chips=None, search_query=""):
        """
        Return everything the board shell needs on first render:
        - stage metadata (id, name, color, sequence)
        - per-stage lead counts
        - KPI header values
        - current user info
        - available salespersons

        Heavy lead payloads are fetched per-column on demand via
        get_stage_leads().
        """
        active_chips = active_chips or []
        domain = self._build_domain(active_chips, search_query)

        # ── Stages ──────────────────────────────────────────────────
        # Only show the 6 dojo pipeline stages, in defined order.
        # If duplicate stage names exist (e.g. Odoo defaults), keep
        # the first one encountered by sequence and aggregate lead counts.
        all_stages = self.env["crm.stage"].search(
            [("name", "in", STAGE_ORDER)], order="sequence asc"
        )
        # Deduplicate: one entry per name; first (lowest sequence) wins
        stage_by_name = {}
        for st in all_stages:
            if st.name not in stage_by_name:
                stage_by_name[st.name] = st

        stage_list = []
        for name in STAGE_ORDER:
            st = stage_by_name.get(name)
            if not st:
                continue
            # Count leads across ALL stages with this name to avoid missing
            # leads that landed on a duplicate stage.
            stage_ids = all_stages.filtered(lambda s: s.name == name).ids
            count = self.env["crm.lead"].search_count(
                domain + [("stage_id", "in", stage_ids), ("active", "=", True)]
            )
            stage_list.append({
                "id":       st.id,
                "name":     st.name,
                "sequence": st.sequence,
                "count":    count,
                "is_won":   st.is_won,
                "folded":   st.fold,
            })

        # ── KPIs ────────────────────────────────────────────────────
        kpis = self._compute_kpis()

        # ── Current user ────────────────────────────────────────────
        me = self.env.user
        current_user = {
            "id":      me.id,
            "name":    me.name,
            "is_manager": me.has_group("sales_team.group_sale_manager"),
        }

        # ── Salesperson options ──────────────────────────────────────
        sales_users = self.env["res.users"].search(
            [("share", "=", False), ("active", "=", True)],
            limit=50,
            order="name",
        )
        salespersons = [{"id": u.id, "name": u.name} for u in sales_users]

        # ── Tag options ──────────────────────────────────────────────
        tags = self.env["crm.tag"].search([], order="name")
        tag_options = [{"id": t.id, "name": t.name} for t in tags]

        return {
            "stages":        stage_list,
            "kpis":          kpis,
            "current_user":  current_user,
            "salespersons":  salespersons,
            "tag_options":   tag_options,
        }

    # ------------------------------------------------------------------
    # Per-stage lead fetch
    # ------------------------------------------------------------------

    @api.model
    def get_stage_leads(self, stage_id, active_chips=None, search_query="", offset=0, limit=20):
        """
        Return paginated leads for a single stage column.
        offset/limit enable infinite-scroll without loading the whole pipeline.
        Aggregates leads across all stages sharing the same name (handles
        Odoo-default duplicate stages).
        """
        active_chips = active_chips or []
        primary = self.env["crm.stage"].browse(stage_id)
        # Collect all stage IDs that share the same pipeline slot name
        sibling_ids = self.env["crm.stage"].search(
            [("name", "=", primary.name)]
        ).ids if primary.exists() else [stage_id]

        domain = self._build_domain(active_chips, search_query) + [
            ("stage_id", "in", sibling_ids),
            ("active", "=", True),
        ]
        total = self.env["crm.lead"].search_count(domain)
        leads = self.env["crm.lead"].search(
            domain,
            order="dojo_lead_score desc, date_deadline asc, id desc",
            offset=offset,
            limit=limit,
        )
        return {
            "stage_id": stage_id,
            "total":    total,
            "leads":    [_lead_dict(l) for l in leads],
        }

    # ------------------------------------------------------------------
    # Single lead detail
    # ------------------------------------------------------------------

    @api.model
    def get_lead_detail(self, lead_id):
        """
        Return a full detail payload for the side panel.
        Includes all dojo fields + waiver info + activity summary.
        """
        lead = self.env["crm.lead"].browse(lead_id)
        if not lead.exists():
            return {"error": "Lead not found"}

        data = _lead_dict(lead)

        # Waiver fields (added by crm_lead_waiver.py)
        data.update({
            "lead_has_signed_waiver": getattr(lead, "lead_has_signed_waiver", False),
            "lead_waiver_signed_by":  getattr(lead, "lead_waiver_signed_by", ""),
            "lead_waiver_signed_on":  (
                str(getattr(lead, "lead_waiver_signed_on", "") or "")
            ),
        })

        # Pending activities summary
        activities = self.env["mail.activity"].search([
            ("res_model", "=", "crm.lead"),
            ("res_id", "=", lead_id),
        ], order="date_deadline asc", limit=10)
        data["activities"] = [
            {
                "id":           a.id,
                "type":         a.activity_type_id.name,
                "summary":      a.summary or "",
                "date_deadline": str(a.date_deadline),
                "overdue":      a.date_deadline < fields.Date.today(),
                "user_name":    a.user_id.name,
                "note":         a.note or "",
            }
            for a in activities
        ]

        # Token details
        data["trial_booking_token"]  = lead.trial_booking_token or ""
        data["trial_cancel_token"]   = lead.trial_cancel_token or ""
        data["trial_token_expires"]  = (
            str(lead.trial_token_expires) if lead.trial_token_expires else ""
        )
        data["trial_reminder_sent"]     = lead.trial_reminder_sent
        data["no_show_followup_sent"]   = lead.no_show_followup_sent
        data["offer_expiry_followup_sent"] = lead.offer_expiry_followup_sent

        return data

    @api.model
    def get_lead_messages(self, lead_id):
        """Return recent chatter messages and log notes for a lead.

        Inline Template tokens (e.g. ``{{ object.contact_name }}``) are
        rendered defensively at display time so legacy/raw-stored bodies show
        the resolved values.
        """
        messages = self.env["mail.message"].search([
            ("res_id", "=", lead_id),
            ("model", "=", "crm.lead"),
            ("message_type", "in", ["comment", "email", "email_outgoing"]),
        ], order="date desc", limit=30)
        mt_note_ref = self.env.ref("mail.mt_note", raise_if_not_found=False)
        mt_note_id = mt_note_ref.id if mt_note_ref else -1
        result = []
        for m in messages:
            body = _render_inline_for_lead(self.env, m.body or "", lead_id)
            subject = _render_inline_for_lead(self.env, m.subject or "", lead_id)
            result.append({
                "id":      m.id,
                "date":    str(m.date),
                "author":  m.author_id.name if m.author_id else (m.email_from or "Unknown"),
                "body":    body,
                "subject": subject,
                "is_note": m.subtype_id.id == mt_note_id,
            })
        return result

    # ------------------------------------------------------------------
    # KPI helper (public so board can refresh without full bootstrap)
    # ------------------------------------------------------------------

    @api.model
    def get_kpis(self):
        return self._compute_kpis()

    def _compute_kpis(self):
        now = datetime.now()

        total_leads = self.env["crm.lead"].search_count([
            ("active", "=", True),
            ("probability", "<", 100),
        ])

        d30 = (now - timedelta(days=30)).strftime("%Y-%m-%d")
        won = self.env["crm.lead"].with_context(active_test=False).search_count([
            ("date_closed", ">=", d30),
            ("probability", "=", 100),
        ])
        all_leads = self.env["crm.lead"].with_context(active_test=False).search_count([
            ("create_date", ">=", d30),
        ])
        conversion_rate = round((won / all_leads) * 100) if all_leads else 0

        week_start = now - timedelta(days=(now.weekday()))
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end   = week_start + timedelta(days=7)
        trials_this_week = self.env["crm.lead"].search_count([
            ("trial_session_id", "!=", False),
            ("trial_session_id.start_datetime", ">=", week_start.strftime("%Y-%m-%d %H:%M:%S")),
            ("trial_session_id.start_datetime", "<",  week_end.strftime("%Y-%m-%d %H:%M:%S")),
        ])

        cutoff = (now - timedelta(days=3)).strftime("%Y-%m-%d")
        expiring_offers = self.env["crm.lead"].search_count([
            ("offer_sent_date", "!=", False),
            ("offer_sent_date", "<=", cutoff),
            ("is_converted", "=", False),
            ("active", "=", True),
        ])

        return {
            "total_leads":      total_leads,
            "conversion_rate":  conversion_rate,
            "trials_this_week": trials_this_week,
            "expiring_offers":  expiring_offers,
        }

    # ------------------------------------------------------------------
    # Single-record mutations
    # ------------------------------------------------------------------

    @api.model
    def move_lead_stage(self, lead_id, stage_id):
        """Move a lead to a new stage. Returns updated lead dict."""
        lead = self.env["crm.lead"].browse(lead_id)
        if not lead.exists():
            raise UserError(_("Lead not found."))
        lead.write({"stage_id": stage_id})
        return _lead_dict(lead)

    @api.model
    def assign_salesperson(self, lead_id, user_id):
        lead = self.env["crm.lead"].browse(lead_id)
        if not lead.exists():
            raise UserError(_("Lead not found."))
        lead.write({"user_id": user_id})
        return _lead_dict(lead)

    @api.model
    def update_lead_field(self, lead_id, field_name, value):
        """Generic single-field update used by the detail panel (trial_attended, no_show, etc.)."""
        ALLOWED = {
            "trial_attended", "no_show", "booking_link_clicked",
            "offer_sent_date", "date_deadline", "priority",
            "partner_name", "contact_name", "email_from", "phone",
            "description",
        }
        if field_name not in ALLOWED:
            raise UserError(_("Field '%s' is not editable via the board.", field_name))
        lead = self.env["crm.lead"].browse(lead_id)
        if not lead.exists():
            raise UserError(_("Lead not found."))
        lead.write({field_name: value})
        return _lead_dict(lead)

    @api.model
    def create_lead(self, vals):
        """Quick-create a new lead from the board.

        - Defaults name to 'Manual Inquiry' if not provided.
        - Auto-creates a res.partner and links it when contact info is given.
        Returns new lead dict.
        """
        allowed_fields = {
            "name", "contact_name", "partner_name", "email_from", "phone",
            "stage_id", "user_id", "tag_ids", "description",
        }
        safe_vals = {k: v for k, v in vals.items() if k in allowed_fields}
        # Default title
        safe_vals.setdefault("name", _("Manual Inquiry"))
        if not safe_vals["name"].strip():
            safe_vals["name"] = _("Manual Inquiry")
        # Default to active user
        safe_vals.setdefault("user_id", self.env.uid)
        safe_vals.setdefault("type", "opportunity")

        # Auto-create a contact (res.partner) when contact info is present
        contact_name = safe_vals.get("contact_name", "").strip()
        email        = safe_vals.get("email_from", "").strip()
        phone        = safe_vals.get("phone", "").strip()
        if contact_name or email:
            partner = self.env["res.partner"].create({
                "name":  contact_name or email,
                "email": email or False,
                "phone": phone or False,
                "customer_rank": 1,
            })
            safe_vals["partner_id"] = partner.id

        lead = self.env["crm.lead"].create(safe_vals)
        return _lead_dict(lead)

    @api.model
    def archive_leads(self, lead_ids, archive=True):
        """Archive or unarchive a list of leads."""
        leads = self.env["crm.lead"].browse(lead_ids)
        leads.write({"active": not archive})
        return {"success": True, "count": len(lead_ids)}

    @api.model
    def update_tags(self, lead_ids, add_tag_ids=None, remove_tag_ids=None):
        """Add/remove tags on one or more leads."""
        add_tag_ids    = add_tag_ids or []
        remove_tag_ids = remove_tag_ids or []
        leads = self.env["crm.lead"].browse(lead_ids)
        commands = []
        if add_tag_ids:
            commands += [(4, tid) for tid in add_tag_ids]
        if remove_tag_ids:
            commands += [(3, tid) for tid in remove_tag_ids]
        if commands:
            leads.write({"tag_ids": commands})
        return {"success": True}

    @api.model
    def post_internal_note(self, lead_id, body):
        """Post an internal note (chatter log note)."""
        lead = self.env["crm.lead"].browse(lead_id)
        if not lead.exists():
            raise UserError(_("Lead not found."))
        lead.message_post(body=body, subtype_xmlid="mail.mt_note")
        return {"success": True}

    @api.model
    def delete_lead(self, lead_id):
        """Permanently delete (unlink) a lead. Requires manager access."""
        lead = self.env["crm.lead"].browse(lead_id)
        if not lead.exists():
            raise UserError(_("Lead not found."))
        lead.unlink()
        return {"success": True}

    @api.model
    def update_partner_avatar(self, lead_id, image_b64):
        """Write a base64-encoded image to the lead's linked partner (image_1920).
        Creates a partner first if one doesn't exist yet.
        Returns updated lead dict."""
        lead = self.env["crm.lead"].browse(lead_id)
        if not lead.exists():
            raise UserError(_("Lead not found."))
        if not lead.partner_id:
            # Create a stub partner and link it
            contact_name = lead.contact_name or lead.partner_name or lead.name
            partner = self.env["res.partner"].create({
                "name": contact_name,
                "email": lead.email_from or False,
                "phone": lead.phone or False,
                "customer_rank": 1,
            })
            lead.write({"partner_id": partner.id})
        lead.partner_id.write({"image_1920": image_b64})
        return _lead_dict(lead)

    @api.model
    def send_message(self, lead_id, body, subject=""):
        """Post an email message on a lead via chatter."""
        lead = self.env["crm.lead"].browse(lead_id)
        if not lead.exists():
            raise UserError(_("Lead not found."))
        lead.message_post(
            body=body,
            subject=subject or False,
            subtype_xmlid="mail.mt_comment",
            message_type="comment",
        )
        return {"success": True}

    # ------------------------------------------------------------------
    # Communications: Call / SMS / Email
    # ------------------------------------------------------------------

    @api.model
    def start_call(self, lead_id):
        """Initiate a call to the lead.

        - If the `connect` (Twilio) module is installed AND the current user
          has a connect.user record, create a connect.call (the connect
          frontend widget will pick it up via its bus channel) and return
          {mode: 'twilio'}.
        - Otherwise return {mode: 'tel', phone: '+1...'} so the frontend
          falls back to a tel: link.
        """
        lead = self.env["crm.lead"].browse(lead_id)
        if not lead.exists():
            raise UserError(_("Lead not found."))
        phone = (lead.phone or "").strip()
        if not phone:
            raise UserError(_("This lead has no phone number."))

        ConnectUser = self.env.get("connect.user")
        if ConnectUser is not None:
            cu = ConnectUser.sudo().search(
                [("user_id", "=", self.env.uid), ("active", "=", True)], limit=1
            )
            if cu:
                try:
                    ConnectCall = self.env["connect.call"].sudo()
                    call = ConnectCall.create({
                        "direction":  "outgoing",
                        "to_number":  phone,
                        "user_id":    self.env.uid,
                        "partner_id": lead.partner_id.id if lead.partner_id else False,
                    })
                    # Best-effort link to lead chatter
                    lead.message_post(
                        body=_("Outbound call started to %s") % phone,
                        subtype_xmlid="mail.mt_note",
                    )
                    return {"mode": "twilio", "call_id": call.id, "phone": phone}
                except Exception as e:
                    _logger.warning("connect.call create failed, falling back to tel: %s", e)
        return {"mode": "tel", "phone": phone}

    @api.model
    def open_email_composer(self, lead_id):
        """Return an ir.actions.act_window payload that opens the standard
        Odoo email composer (mail.compose.message) wired to this lead.
        Frontend hands this to action_service.doAction()."""
        lead = self.env["crm.lead"].browse(lead_id)
        if not lead.exists():
            raise UserError(_("Lead not found."))
        return {
            "type":       "ir.actions.act_window",
            "name":       _("Send Email"),
            "res_model":  "mail.compose.message",
            "view_mode":  "form",
            "views":      [[False, "form"]],
            "target":     "new",
            "context": {
                "default_model":            "crm.lead",
                "default_res_ids":          [lead_id],
                "default_composition_mode": "comment",
                "default_partner_ids":      [lead.partner_id.id] if lead.partner_id else [],
                "default_email_from":       self.env.user.email_formatted or False,
                "default_subject":          lead.name or "",
                "mail_post_autofollow":     True,
            },
        }

    @api.model
    def send_recap_email(self, lead_id):
        """Open the email composer with a personalised recap body pre-filled.

        Pulls lead state (name, trial status, last engagement, notes) and
        composes a short narrative the user can review and tweak before sending.
        Also marks any open 'recap' mail.activity as the default activity to
        complete on send so the To-Do is auto-cleared.
        """
        lead = self.env["crm.lead"].browse(lead_id)
        if not lead.exists():
            raise UserError(_("Lead not found."))

        first_name = (lead.contact_name or lead.partner_name or lead.name or "").split(" ")[0] or "there"
        sender = self.env.user.name or "the team"
        dojo_name = self.env.company.name or "the dojo"

        lines = [f"<p>Hi {first_name},</p>"]
        lines.append(f"<p>Thanks for your interest in {dojo_name} — wanted to send a quick recap of where we are.</p>")

        bullets = []
        if lead.trial_session_id:
            session = lead.trial_session_id
            when = ""
            if session.start_datetime:
                try:
                    when = fields.Datetime.context_timestamp(self, session.start_datetime).strftime("%A %b %-d at %-I:%M %p")
                except Exception:
                    when = str(session.start_datetime)
            if lead.trial_attended:
                bullets.append(f"You came to your trial class ({session.name}{', ' + when if when else ''}) — hope you enjoyed it!")
            elif lead.no_show:
                bullets.append(f"Your trial class on {when or session.name} was missed — happy to rebook whenever works.")
            else:
                bullets.append(f"Your trial is booked for <strong>{when or session.name}</strong>.")
        else:
            bullets.append("You can still book your free trial class anytime.")

        if lead.offer_sent_date:
            bullets.append(f"We sent over a membership offer on {lead.offer_sent_date}.")
        if lead.dojo_member_id:
            bullets.append("You're already enrolled — welcome to the family!")

        if bullets:
            lines.append("<ul>")
            for b in bullets:
                lines.append(f"<li>{b}</li>")
            lines.append("</ul>")

        if lead.description:
            note = _html_to_plain(lead.description)
            if note:
                # Show up to first 240 chars of internal note as private context the
                # rep can read; trim before sending. We DON'T include them in the
                # email body — they're in the composer for convenience only.
                pass

        lines.append("<p>Let me know if you have any questions — happy to help.</p>")

        # ── Personalised marketing-card CTAs ────────────────────────────────
        # Inject up to 3 active publishable static cards (donate/merch/tournament).
        # Skip donate cards if the lead is already an enrolled member.
        card_block = self._render_recap_card_block(lead)
        if card_block:
            lines.append(card_block)

        lines.append(f"<p>— {sender}</p>")
        body = "".join(lines)

        # If there's an open mail.activity whose summary mentions "recap",
        # default the composer to mark it done on send.
        recap_activity = self.env["mail.activity"].search([
            ("res_model", "=", "crm.lead"),
            ("res_id", "=", lead_id),
            ("user_id", "=", self.env.uid),
        ], limit=1)
        # broader fallback: any activity whose summary contains "recap"
        if not recap_activity or "recap" not in (recap_activity.summary or "").lower():
            match = self.env["mail.activity"].search([
                ("res_model", "=", "crm.lead"),
                ("res_id", "=", lead_id),
            ], limit=10)
            recap_activity = match.filtered(lambda a: "recap" in (a.summary or "").lower())[:1]

        ctx = {
            "default_model":            "crm.lead",
            "default_res_ids":          [lead_id],
            "default_composition_mode": "comment",
            "default_partner_ids":      [lead.partner_id.id] if lead.partner_id else [],
            "default_email_from":       self.env.user.email_formatted or False,
            "default_subject":          _("Quick recap from %s") % dojo_name,
            "default_body":             body,
            "mail_post_autofollow":     True,
        }
        if recap_activity:
            ctx["default_mail_activity_type_id"] = recap_activity.activity_type_id.id
            ctx["mark_recap_activity_id"] = recap_activity.id

        return {
            "type":       "ir.actions.act_window",
            "name":       _("Send Recap Email"),
            "res_model":  "mail.compose.message",
            "view_mode":  "form",
            "views":      [[False, "form"]],
            "target":     "new",
            "context":    ctx,
        }

    @api.model
    def complete_recap_activity(self, activity_id):
        """Mark a 'recap' mail.activity as done. Called after the composer closes."""
        if not activity_id:
            return False
        act = self.env["mail.activity"].browse(activity_id)
        if act.exists():
            act.action_done()
            return True
        return False

    @api.model
    def list_templates(self):
        """Return all email + SMS templates that target crm.lead.

        Used by the top-level Templates button on the CRM board so the user
        can jump from a CRM context to the Email Marketing / SMS Marketing
        template forms without per-lead rendering.
        """
        results = {"email": [], "sms": []}

        mail_templates = self.env["mail.template"].sudo().search(
            [("model", "=", "crm.lead")],
            order="name",
        )
        for tpl in mail_templates:
            card = tpl.card_campaign_id
            results["email"].append({
                "id": tpl.id,
                "name": tpl.name or _("Untitled email template"),
                "subject": tpl.subject or "",
                "use_default_to": tpl.use_default_to,
                "card_campaign_id": card.id if card else False,
                "card_campaign_name": card.name if card else "",
            })

        SmsTemplate = self.env.get("sms.template")
        if SmsTemplate is not None:
            sms_templates = SmsTemplate.sudo().search(
                [("model", "=", "crm.lead")],
                order="name",
            )
            for tpl in sms_templates:
                card = tpl.card_campaign_id
                results["sms"].append({
                    "id": tpl.id,
                    "name": tpl.name or _("Untitled SMS template"),
                    "body_preview": (tpl.body or "")[:120],
                    "card_campaign_id": card.id if card else False,
                    "card_campaign_name": card.name if card else "",
                })

        return results

    def _render_recap_card_block(self, lead):
        """Render up to 2 personalised marketing cards as inline email CTAs.

        Uses the standard Odoo Marketing Card module (`card.campaign` /
        `card.card`) to generate per-lead personalised card images and
        redirect URLs. Requires `marketing_card` module + at least one
        active campaign with `res_model = "crm.lead"`.
        Returns "" when nothing is eligible (graceful degradation).
        """
        Campaign = self.env.get("card.campaign")
        if Campaign is None:
            return ""

        campaigns = Campaign.sudo().search(
            [("res_model", "=", "crm.lead")],
            order="id desc",
            limit=2,
        )
        if not campaigns:
            return ""

        accent = "#5D8DA8"

        cells = []
        for camp in campaigns:
            try:
                camp._update_cards([("id", "=", lead.id)])
            except Exception as e:
                _logger.warning(
                    "Marketing card render failed for campaign %s lead %s: %s",
                    camp.id, lead.id, e,
                )
                continue
            card = self.env["card.card"].sudo().search([
                ("campaign_id", "=", camp.id),
                ("res_id", "=", lead.id),
            ], limit=1)
            if not card or not card.image:
                continue
            img_url = card._get_card_url()
            redirect_url = card._get_redirect_url()
            title = (camp.name or "Personal Card").strip()
            cells.append(
                '<td style="padding:6px;vertical-align:top;width:50%;">'
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
                '</td></tr></table></td>'
            )

        if not cells:
            return ""

        return (
            '<div style="margin:18px 0 10px 0;font-size:13px;color:#6b7280;'
            'text-transform:uppercase;letter-spacing:0.04em;font-weight:600;">'
            'A little something for you</div>'
            '<table cellpadding="0" cellspacing="0" border="0" width="100%" '
            'style="border-collapse:separate;border-spacing:0;margin-bottom:10px;">'
            f'<tr>{"".join(cells)}</tr></table>'
        )

    @api.model
    def open_sms_composer(self, lead_id):
        """Return an ir.actions.act_window payload that opens the standard
        Odoo SMS composer (sms.composer) wired to this lead."""
        lead = self.env["crm.lead"].browse(lead_id)
        if not lead.exists():
            raise UserError(_("Lead not found."))
        return {
            "type":       "ir.actions.act_window",
            "name":       _("Send SMS"),
            "res_model":  "sms.composer",
            "view_mode":  "form",
            "views":      [[False, "form"]],
            "target":     "new",
            "context": {
                "default_res_model":     "crm.lead",
                "default_res_ids":       repr([lead_id]),
                "default_composition_mode": "comment",
                "default_recipient_single_number": lead.phone or "",
            },
        }

    # ------------------------------------------------------------------
    # Notes (rich-text description on crm.lead)
    # ------------------------------------------------------------------

    @api.model
    def update_lead_description(self, lead_id, text):
        """Save free-form notes to crm.lead.description.

        Stores plain text wrapped in a single <p> with line breaks preserved
        so the field-level HTML sanitizer doesn't mangle the textarea content.
        Returns the plain-text round-trip so the OWL state stays consistent.
        """
        from markupsafe import escape, Markup
        lead = self.env["crm.lead"].browse(lead_id)
        if not lead.exists():
            raise UserError(_("Lead not found."))
        plain = (text or "").strip()
        if plain:
            html = Markup("<p>%s</p>") % Markup(escape(plain).replace("\n", Markup("<br/>")))
            lead.write({"description": str(html)})
        else:
            lead.write({"description": False})
        return {"success": True, "description": plain}

    @api.model
    def update_lead_contact(self, lead_id, vals):
        """Inline-edit a lead's contact details from the pipeline modal.

        Accepts whitelisted keys only: contact_name, email_from, phone.
        Returns the saved values for OWL state sync.
        """
        ALLOWED = {"contact_name", "email_from", "phone"}
        clean = {k: (v.strip() if isinstance(v, str) else v) or False
                 for k, v in (vals or {}).items() if k in ALLOWED}
        if not clean:
            return {"success": False}
        lead = self.env["crm.lead"].browse(lead_id)
        if not lead.exists():
            raise UserError(_("Lead not found."))
        lead.write(clean)
        return {
            "success": True,
            "contact_name": lead.contact_name or "",
            "email_from":   lead.email_from or "",
            "phone":        lead.phone or "",
        }

    # ------------------------------------------------------------------
    # Automations panel (toggles ir.cron.active for known CRM crons)
    # ------------------------------------------------------------------
    # Map of UI-key -> ir.cron xml_id. Add/remove as crons are added.
    _CRM_AUTOMATIONS = [
        {
            "key":   "trial_reminders",
            "label": "Trial Reminder Email",
            "description": "Email + SMS sent ~24h before a booked trial session.",
            "xml_id": "dojo_crm.ir_cron_crm_trial_reminders",
        },
        {
            "key":   "no_show",
            "label": "No-Show Detection",
            "description": "Marks a lead as No-Show 48h after a missed Trial Booked.",
            "xml_id": "dojo_crm.ir_cron_crm_no_show",
        },
        {
            "key":   "no_show_followup",
            "label": "No-Show 2nd Follow-Up",
            "description": "Second follow-up email 5 days after a no-show.",
            "xml_id": "dojo_crm.ir_cron_crm_no_show_followup",
        },
        {
            "key":   "offer_expiry",
            "label": "Offer Expiry & Auto-Lost",
            "description": "Nudges leads 72h after an offer; auto-loses after 7 days.",
            "xml_id": "dojo_crm.ir_cron_crm_offer_expiry",
        },
        {
            "key":   "trial_expiry",
            "label": "Missed Trials → Evaluation",
            "description": "Moves leads with passed trial sessions into Evaluation.",
            "xml_id": "dojo_crm.ir_cron_crm_trial_expiry",
        },
        {
            "key":   "auto_qualify",
            "label": "Auto-Qualify Hot Leads",
            "description": "Promotes leads with score ≥ 60 to Qualified automatically.",
            "xml_id": "dojo_crm.ir_cron_crm_auto_qualify",
        },
        {
            "key":   "winback",
            "label": "Win-Back No-Show Evaluation",
            "description": "Re-engages no-show Evaluation leads weekly.",
            "xml_id": "dojo_crm.ir_cron_crm_winback",
        },
        {
            "key":   "stale_leads",
            "label": "Stale Lead Cleanup",
            "description": "Nudges new leads at 14 days, archives at 30.",
            "xml_id": "dojo_crm.ir_cron_crm_stale_leads",
        },
    ]

    def _resolve_automation_cron(self, xml_id):
        """Return the ir.cron record for a given xml_id, or empty recordset."""
        try:
            return self.env.ref(xml_id, raise_if_not_found=False) or self.env["ir.cron"]
        except Exception:
            return self.env["ir.cron"]

    @api.model
    def get_crm_automations(self):
        """Return list of CRM automations with their current enabled state."""
        is_admin = self.env.user.has_group("base.group_system")
        out = []
        for cfg in self._CRM_AUTOMATIONS:
            cron = self._resolve_automation_cron(cfg["xml_id"])
            exists = bool(cron and cron._name == "ir.cron")
            out.append({
                "key":         cfg["key"],
                "label":       cfg["label"],
                "description": cfg["description"],
                "enabled":     bool(cron.active) if exists else False,
                "exists":      exists,
                "last_run":    str(cron.lastcall) if exists and cron.lastcall else "",
                "next_run":    str(cron.nextcall) if exists and cron.nextcall else "",
                "interval":    (
                    "%d %s" % (cron.interval_number, cron.interval_type)
                    if exists else ""
                ),
            })
        return {"automations": out, "is_admin": is_admin}

    @api.model
    def set_crm_automation(self, key, enabled):
        """Toggle an ir.cron.active for a known CRM automation. Admin-only."""
        if not self.env.user.has_group("base.group_system"):
            raise AccessError(_("Only administrators can change automations."))
        cfg = next((c for c in self._CRM_AUTOMATIONS if c["key"] == key), None)
        if not cfg:
            raise UserError(_("Unknown automation: %s", key))
        cron = self._resolve_automation_cron(cfg["xml_id"])
        if not cron or cron._name != "ir.cron":
            raise UserError(_("Automation cron not found."))
        cron.sudo().write({"active": bool(enabled)})
        return {"success": True, "key": key, "enabled": bool(enabled)}



    @api.model
    def bulk_move_stage(self, lead_ids, stage_id):
        leads = self.env["crm.lead"].browse(lead_ids)
        leads.write({"stage_id": stage_id})
        return {"success": True, "count": len(lead_ids)}

    @api.model
    def bulk_assign_salesperson(self, lead_ids, user_id):
        leads = self.env["crm.lead"].browse(lead_ids)
        leads.write({"user_id": user_id})
        return {"success": True, "count": len(lead_ids)}

    @api.model
    def bulk_post_note(self, lead_ids, body):
        for lead in self.env["crm.lead"].browse(lead_ids):
            rendered_body = _render_inline_for_lead(self.env, body, lead.id)
            lead.message_post(
                body=rendered_body,
                subtype_xmlid="mail.mt_note",
                message_type="comment",
            )
        return {"success": True, "count": len(lead_ids)}

    @api.model
    def bulk_send_message(self, lead_ids, body, subject=""):
        for lead in self.env["crm.lead"].browse(lead_ids):
            rendered_body = _render_inline_for_lead(self.env, body, lead.id)
            rendered_subject = _render_inline_for_lead(self.env, subject, lead.id) if subject else ""
            lead.message_post(
                body=rendered_body,
                subject=rendered_subject or False,
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
            )
        return {"success": True, "count": len(lead_ids)}

    @api.model
    def bulk_archive(self, lead_ids, archive=True):
        return self.archive_leads(lead_ids, archive=archive)

    @api.model
    def bulk_update_tags(self, lead_ids, add_tag_ids=None, remove_tag_ids=None):
        return self.update_tags(lead_ids, add_tag_ids=add_tag_ids, remove_tag_ids=remove_tag_ids)

    # ------------------------------------------------------------------
    # Book Trial — called from the custom Book Trial modal
    # ------------------------------------------------------------------

    @api.model
    def book_trial(self, lead_id, session_id, force=False):
        """
        Create a transient dojo.book.trial.wizard record and call
        action_confirm() so all existing validation and side-effects fire.
        """
        wizard = self.env["dojo.book.trial.wizard"].with_context(
            default_lead_id=lead_id
        ).create({
            "lead_id":    lead_id,
            "session_id": session_id,
            "force_book": force,
        })
        # action_confirm raises UserError on capacity violation unless force=True
        wizard.action_confirm()
        return _lead_dict(self.env["crm.lead"].browse(lead_id))

    @api.model
    def get_available_sessions(self, limit=20):
        """Return upcoming open/draft sessions for the Book Trial modal session picker."""
        sessions = self.env["dojo.class.session"].search(
            [("state", "in", ["draft", "open"])],
            order="start_datetime asc",
            limit=limit,
        )
        result = []
        for s in sessions:
            capacity   = getattr(s, "capacity", 0) or 0
            seats_taken = getattr(s, "seats_taken", 0) or 0
            template_name = ""
            if hasattr(s, "template_id") and s.template_id:
                template_name = s.template_id.name or ""
            result.append({
                "id":             s.id,
                "name":           s.name or "",
                "start_datetime": str(s.start_datetime) if s.start_datetime else "",
                "capacity":       capacity,
                "seats_taken":    seats_taken,
                "seats_left":     max(0, capacity - seats_taken),
                "is_full":        bool(capacity and seats_taken >= capacity),
                "template_name":  template_name,
            })
        return result

    # ------------------------------------------------------------------
    # Domain builder
    # ------------------------------------------------------------------

    def _build_domain(self, active_chips, search_query):
        domain = []
        for chip in active_chips:
            chip_domain = _CHIP_DOMAINS.get(chip)
            if chip_domain:
                domain += chip_domain
        if search_query:
            q = search_query.strip()
            domain += [
                "|", "|", "|",
                ("contact_name", "ilike", q),
                ("partner_name", "ilike", q),
                ("email_from", "ilike", q),
                ("phone", "ilike", q),
            ]
        return domain
