import logging
import re

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class DojoTrialBooking(http.Controller):
    """Public-facing trial booking and management pages."""

    # ── Helpers ──────────────────────────────────────────────────────────

    def _get_lead_by_booking_token(self, token):
        if not token:
            return None
        lead = (
            request.env["crm.lead"]
            .sudo()
            .search([("trial_booking_token", "=", token)], limit=1)
        )
        return lead if lead.exists() else None

    def _get_lead_by_manage_token(self, token):
        if not token:
            return None
        lead = (
            request.env["crm.lead"]
            .sudo()
            .search([("trial_cancel_token", "=", token)], limit=1)
        )
        return lead if lead.exists() else None

    def _get_trial_sessions(self):
        """Return upcoming open trial-program sessions with available capacity.

        Trial sessions are identified by their program's `is_trial` flag.
        Owners enable this on the program record in the Classes configuration.
        """
        from odoo import fields as odoo_fields

        now = odoo_fields.Datetime.now()
        sessions = (
            request.env["dojo.class.session"]
            .sudo()
            .search(
                [
                    ("template_id.program_id.is_trial", "=", True),
                    ("state", "in", ["draft", "open"]),
                    ("start_datetime", ">", now),
                ],
                order="start_datetime asc",
                limit=30,
            )
        )
        return sessions

    # ── Book Trial ───────────────────────────────────────────────────────

    @http.route(
        "/trial/book/<string:token>",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def trial_book_page(self, token, **kw):
        lead = self._get_lead_by_booking_token(token)
        if not lead:
            return request.render("dojo_crm.trial_token_expired")

        from odoo import fields as odoo_fields

        if lead.trial_token_expires and lead.trial_token_expires < odoo_fields.Datetime.now():
            return request.render("dojo_crm.trial_token_expired")

        # Already booked?
        if lead.trial_session_id:
            return request.render(
                "dojo_crm.trial_book_already",
                {"lead": lead, "session": lead.trial_session_id},
            )

        sessions = self._get_trial_sessions()
        return request.render(
            "dojo_crm.trial_book_page",
            {
                "lead": lead,
                "sessions": sessions,
                "error": kw.get("error"),
            },
        )

    @http.route(
        "/trial/book/<string:token>/confirm",
        type="http",
        auth="public",
        website=True,
        methods=["POST"],
        csrf=True,
        sitemap=False,
    )
    def trial_book_confirm(self, token, **kw):
        lead = self._get_lead_by_booking_token(token)
        if not lead:
            return request.render("dojo_crm.trial_token_expired")

        from odoo import fields as odoo_fields

        if lead.trial_token_expires and lead.trial_token_expires < odoo_fields.Datetime.now():
            return request.render("dojo_crm.trial_token_expired")

        session_id = int(kw.get("session_id", 0))
        if not session_id:
            return request.redirect(f"/trial/book/{token}?error=Please+select+a+session")

        session = (
            request.env["dojo.class.session"]
            .sudo()
            .browse(session_id)
            .exists()
        )
        if not session or session.state not in ("draft", "open"):
            return request.redirect(f"/trial/book/{token}?error=Session+no+longer+available")

        if session.seats_taken >= session.capacity:
            return request.redirect(f"/trial/book/{token}?error=Session+is+full")

        # If they haven't signed the waiver yet, redirect to the waiver page first.
        if not lead.lead_has_signed_waiver:
            return request.redirect(
                f"/trial/book/{token}/waiver?session_id={session_id}"
            )

        # Waiver already on file — book the trial directly.
        return self._do_book_trial(token, lead, session)

    # ── Waiver signing step ───────────────────────────────────────────────

    @http.route(
        "/trial/book/<string:token>/waiver",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def trial_waiver_page(self, token, **kw):
        """Display the liability waiver for the prospect to read and sign."""
        lead = self._get_lead_by_booking_token(token)
        if not lead:
            return request.render("dojo_crm.trial_token_expired")

        from odoo import fields as odoo_fields

        if lead.trial_token_expires and lead.trial_token_expires < odoo_fields.Datetime.now():
            return request.render("dojo_crm.trial_token_expired")

        session_id = int(kw.get("session_id", 0))
        if not session_id:
            return request.redirect(f"/trial/book/{token}?error=Please+select+a+session")

        session = (
            request.env["dojo.class.session"]
            .sudo()
            .browse(session_id)
            .exists()
        )
        if not session or session.state not in ("draft", "open"):
            return request.redirect(f"/trial/book/{token}?error=Session+no+longer+available")

        waiver_config = (
            request.env["dojo.waiver.config"]
            .sudo()
            .get_singleton()
        )

        return request.render(
            "dojo_crm.trial_waiver_page",
            {
                "lead": lead,
                "session": session,
                "waiver_config": waiver_config,
                "error": kw.get("error"),
            },
        )

    @http.route(
        "/trial/book/<string:token>/waiver",
        type="http",
        auth="public",
        website=True,
        methods=["POST"],
        csrf=True,
        sitemap=False,
    )
    def trial_waiver_submit(self, token, **kw):
        """Validate and store the signed waiver, then book the trial."""
        lead = self._get_lead_by_booking_token(token)
        if not lead:
            return request.render("dojo_crm.trial_token_expired")

        from odoo import fields as odoo_fields

        if lead.trial_token_expires and lead.trial_token_expires < odoo_fields.Datetime.now():
            return request.render("dojo_crm.trial_token_expired")

        session_id = int(kw.get("session_id", 0))
        if not session_id:
            return request.redirect(f"/trial/book/{token}?error=Please+select+a+session")

        session = (
            request.env["dojo.class.session"]
            .sudo()
            .browse(session_id)
            .exists()
        )
        if not session or session.state not in ("draft", "open"):
            return request.redirect(f"/trial/book/{token}?error=Session+no+longer+available")

        if session.seats_taken >= session.capacity:
            return request.redirect(
                f"/trial/book/{token}?error=Session+is+full"
            )

        # ── Validate waiver inputs ──────────────────────────────────────────
        signed_by = (kw.get("signed_by") or "").strip()
        agreed = kw.get("agreed")
        signature_data = (kw.get("signature_data") or "").strip()

        error = None
        if not agreed:
            error = "You must tick the agreement checkbox to proceed."
        elif not signed_by:
            error = "Please enter your full name in the 'Signing as' field."
        elif not signature_data or signature_data == "data:,":
            error = "A drawn signature is required. Please sign in the box above."

        if error:
            import urllib.parse
            return request.redirect(
                f"/trial/book/{token}/waiver?session_id={session_id}"
                f"&error={urllib.parse.quote(error)}"
            )

        # ── Strip the data-URI prefix and store as binary ──────────────────
        import base64
        if "," in signature_data:
            signature_data = signature_data.split(",", 1)[1]
        try:
            signature_bytes = base64.b64decode(signature_data)
            # Re-encode as a clean base64 string (Odoo Image field expects this)
            signature_b64 = base64.b64encode(signature_bytes).decode("ascii")
        except Exception:
            return request.redirect(
                f"/trial/book/{token}/waiver?session_id={session_id}"
                "&error=Invalid+signature+data.+Please+try+again."
            )

        remote_ip = (
            request.httprequest.environ.get("HTTP_X_FORWARDED_FOR", "")
            .split(",")[0]
            .strip()
            or request.httprequest.remote_addr
            or ""
        )

        lead.sudo().write(
            {
                "lead_waiver_signature": signature_b64,
                "lead_waiver_signed_by": signed_by,
                "lead_waiver_signed_on": odoo_fields.Datetime.now(),
                "lead_waiver_ip": remote_ip,
                "booking_link_clicked": True,
            }
        )

        lead.message_post(
            body=(
                f"Waiver signed via public portal by {signed_by} "
                f"(IP: {remote_ip})"
            ),
            subtype_xmlid="mail.mt_note",
        )

        return self._do_book_trial(token, lead, session)

    # ── Shared booking helper ─────────────────────────────────────────────

    def _do_book_trial(self, token, lead, session):
        """Write the trial booking, advance the stage, and return the confirmation page."""
        trial_booked_stage = (
            request.env["crm.stage"]
            .sudo()
            .search([("name", "=", "Trial Booked")], limit=1)
        )
        vals = {
            "trial_session_id": session.id,
            "trial_reminder_sent": False,
            "booking_link_clicked": True,
        }
        if trial_booked_stage:
            vals["stage_id"] = trial_booked_stage.id
        lead.write(vals)

        lead.message_post(
            body=f"Trial booked via public link: {session.name} on {session.start_datetime}",
            subtype_xmlid="mail.mt_note",
        )

        return request.render(
            "dojo_crm.trial_book_confirm_page",
            {"lead": lead, "session": session},
        )

    # ── Manage (Cancel / Reschedule) ─────────────────────────────────────

    @http.route(
        "/trial/manage/<string:token>",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def trial_manage_page(self, token, **kw):
        lead = self._get_lead_by_manage_token(token)
        if not lead:
            return request.render("dojo_crm.trial_token_expired")

        if not lead.trial_session_id:
            return request.render(
                "dojo_crm.trial_manage_no_booking",
                {"lead": lead},
            )

        sessions = self._get_trial_sessions()
        return request.render(
            "dojo_crm.trial_manage_page",
            {
                "lead": lead,
                "session": lead.trial_session_id,
                "sessions": sessions,
                "error": kw.get("error"),
                "success": kw.get("success"),
            },
        )

    @http.route(
        "/trial/manage/<string:token>/cancel",
        type="http",
        auth="public",
        website=True,
        methods=["POST"],
        csrf=True,
        sitemap=False,
    )
    def trial_manage_cancel(self, token, **kw):
        lead = self._get_lead_by_manage_token(token)
        if not lead or not lead.trial_session_id:
            return request.render("dojo_crm.trial_token_expired")

        old_session = lead.trial_session_id.name
        qualified_stage = (
            request.env["crm.stage"]
            .sudo()
            .search([("name", "=", "Qualified")], limit=1)
        )
        vals = {
            "trial_session_id": False,
            "trial_reminder_sent": False,
            "no_show": False,
        }
        if qualified_stage:
            vals["stage_id"] = qualified_stage.id
        lead.write(vals)

        lead.message_post(
            body=f"Trial cancelled via manage link (was: {old_session})",
            subtype_xmlid="mail.mt_note",
        )

        return request.redirect(
            f"/trial/manage/{token}?success=Your+trial+has+been+cancelled"
        )

    @http.route(
        "/trial/manage/<string:token>/reschedule",
        type="http",
        auth="public",
        website=True,
        methods=["POST"],
        csrf=True,
        sitemap=False,
    )
    def trial_manage_reschedule(self, token, **kw):
        lead = self._get_lead_by_manage_token(token)
        if not lead:
            return request.render("dojo_crm.trial_token_expired")

        session_id = int(kw.get("session_id", 0))
        if not session_id:
            return request.redirect(
                f"/trial/manage/{token}?error=Please+select+a+new+session"
            )

        session = (
            request.env["dojo.class.session"]
            .sudo()
            .browse(session_id)
            .exists()
        )
        if not session or session.state not in ("draft", "open"):
            return request.redirect(
                f"/trial/manage/{token}?error=Session+no+longer+available"
            )

        if session.seats_taken >= session.capacity:
            return request.redirect(
                f"/trial/manage/{token}?error=Session+is+full"
            )

        old_session = lead.trial_session_id.name if lead.trial_session_id else "None"
        trial_booked_stage = (
            request.env["crm.stage"]
            .sudo()
            .search([("name", "=", "Trial Booked")], limit=1)
        )
        vals = {
            "trial_session_id": session.id,
            "trial_reminder_sent": False,
            "no_show": False,
        }
        if trial_booked_stage:
            vals["stage_id"] = trial_booked_stage.id
        lead.write(vals)

        lead.message_post(
            body=f"Trial rescheduled via manage link: {old_session} → {session.name}",
            subtype_xmlid="mail.mt_note",
        )

        return request.redirect(
            f"/trial/manage/{token}?success=Your+trial+has+been+rescheduled"
        )

    @http.route(
        "/trial/submit",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
        methods=["POST"],
        csrf=True,
    )
    def trial_signup_submit(self, **kw):
        """Handle trial sign-up form submission — creates a New Lead in CRM.

        Accepts an optional ``success_url`` POST field so embedded forms on
        other pages can redirect to their own thank-you page instead of the
        default dojo_crm success template.
        """
        name = (kw.get("name") or "").strip()
        email = (kw.get("email") or "").strip()
        phone = (kw.get("phone") or "").strip()
        discipline = (kw.get("discipline") or "").strip()
        message = (kw.get("message") or "").strip()
        # Where to send the visitor after a successful submission.
        # Embedded forms pass their own thank-you URL; standalone /trial page uses None.
        success_url = (kw.get("success_url") or "").strip() or None
        # Where to redirect on validation error (default: the standalone /trial page).
        error_url = (kw.get("error_url") or "/trial").strip()

        # Basic validation
        if not name or not email:
            return request.redirect(f"{error_url}?error=Please+provide+your+name+and+email+address")

        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            return request.redirect(f"{error_url}?error=Please+provide+a+valid+email+address")

        # Resolve tags
        discipline_tag_map = {
            # Taekwondo programs (United Family Taekwondo)
            "preschool_tkd": "Preschool Taekwondo",
            "kids_tkd": "Kids Taekwondo",
            "teen_adult_tkd": "Teen & Adult Taekwondo",
            # Legacy / multi-discipline values kept for backwards compatibility
            "adult_bjj": "Adult BJJ",
            "kids_bjj": "Kids BJJ",
            "muay_thai": "Muay Thai",
        }
        tag_ids = []

        online_tag = (
            request.env["crm.tag"].sudo().search([("name", "=", "Online")], limit=1)
        )
        if online_tag:
            tag_ids.append((4, online_tag.id))

        # Resolve discipline tag: slug key → mapped name, or use value directly as tag name
        disc_tag_name = discipline_tag_map.get(discipline, discipline)
        if disc_tag_name:
            disc_tag = (
                request.env["crm.tag"]
                .sudo()
                .search([("name", "=ilike", disc_tag_name)], limit=1)
            )
            if not disc_tag:
                disc_tag = request.env["crm.tag"].sudo().create({"name": disc_tag_name})
            tag_ids.append((4, disc_tag.id))

        # Find "New" stage (matches crm_stage.xml)
        new_lead_stage = (
            request.env["crm.stage"]
            .sudo()
            .search([("name", "=", "New")], limit=1)
        )

        # Resolve the salesperson from the trial program's instructor.
        # We look for a trial program whose name also matches the chosen discipline
        # (e.g. "Free Trial – Adult BJJ") and fall back to any trial program.
        salesperson_id = False
        disc_name = discipline_tag_map.get(discipline, discipline)
        trial_program = (
            request.env["dojo.program"]
            .sudo()
            .search(
                [("name", "ilike", "trial"), ("name", "ilike", disc_name)],
                limit=1,
            )
            if disc_name
            else request.env["dojo.program"].sudo().browse()
        )
        if not trial_program:
            # Fall back to any program with "trial" in the name
            trial_program = (
                request.env["dojo.program"]
                .sudo()
                .search([("name", "ilike", "trial")], limit=1)
            )
        if trial_program:
            # Use the program's dedicated instructor first, then fall back to courses
            instructor = trial_program.manager_instructor_id
            if not instructor:
                instructor = (
                    request.env["dojo.class.template"]
                    .sudo()
                    .search(
                        [("program_id", "=", trial_program.id),
                         ("recurrence_instructor_id", "!=", False)],
                        limit=1,
                    )
                    .recurrence_instructor_id
                )
            if not instructor:
                instructor = (
                    request.env["dojo.class.template"]
                    .sudo()
                    .search(
                        [("program_id", "=", trial_program.id),
                         ("instructor_profile_ids", "!=", False)],
                        limit=1,
                    )
                    .instructor_profile_ids[:1]
                )
            if instructor and instructor.user_id:
                salesperson_id = instructor.user_id.id

        # Find or create a res.partner so automations (no-show email, SMS fallback) work
        Partner = request.env["res.partner"].sudo()
        partner = Partner.search([("email", "=ilike", email)], limit=1)
        if not partner:
            partner_vals = {"name": name, "email": email, "is_company": False}
            if phone:
                partner_vals["phone"] = phone
            partner = Partner.create(partner_vals)
        else:
            if phone and not partner.phone:
                partner.write({"phone": phone})

        vals = {
            "name": f"Free Trial — {name}",
            "contact_name": name,
            "email_from": email,
            "partner_id": partner.id,
        }
        if salesperson_id:
            vals["user_id"] = salesperson_id
        if phone:
            vals["phone"] = phone
        if tag_ids:
            vals["tag_ids"] = tag_ids
        if new_lead_stage:
            vals["stage_id"] = new_lead_stage.id
        if message:
            vals["description"] = message

        lead = request.env["crm.lead"].sudo().create(vals)
        lead._generate_trial_tokens()
        lead.message_post(
            body="Lead created via website trial sign-up form.",
            subtype_xmlid="mail.mt_note",
        )

        return request.redirect(success_url or "/")
