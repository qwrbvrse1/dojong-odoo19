import json

from odoo import http
from odoo.http import request


class PortalOpsDemoController(http.Controller):
    def _get_google_maps_browser_api_key(self):
        icp = request.env["ir.config_parameter"].sudo()
        return (
            icp.get_str("portalops_demo.google_maps_browser_api_key", "")
            or icp.get_str("portalops_demo.google_maps_grounding_api_key", "")
            or ""
        )

    def _get_location(self, slug):
        location = (
            request.env["portalops.demo.location"]
            .sudo()
            .search([("slug", "=", slug), ("is_published", "=", True)], limit=1)
        )
        return location if location.exists() else None

    def _cards_for_perspective(self, location, perspective):
        cards = location.card_ids.sorted(key=lambda rec: (rec.sequence, rec.id))
        if not perspective:
            return cards
        return cards.filtered(lambda rec: rec.visibility in ("all", perspective))

    def _serialize_card(self, card):
        return {
            "id": card.id,
            "name": card.name,
            "headline": card.headline or "",
            "body": card.body or "",
            "kind": card.kind or "insight",
            "sequence": card.sequence,
            "visibility": card.visibility,
        }

    def _serialize_audit_event(self, event):
        return {
            "id": event.id,
            "event_type": event.event_type,
            "title": event.title,
            "detail": event.detail or "",
            "created_at": event.create_date.isoformat() if event.create_date else None,
            "sequence": event.sequence,
        }

    def _serialize_location(self, location, perspective="patient"):
        cards = self._cards_for_perspective(location, perspective)
        audit_events = location.audit_event_ids.sorted(key=lambda rec: (rec.sequence, rec.id))
        return {
            "slug": location.slug,
            "name": location.name,
            "headline": location.headline or "",
            "summary": location.summary or "",
            "address_line": location.address_line or "",
            "city": location.city or "",
            "state_code": location.state_code or "",
            "postal_code": location.postal_code or "",
            "country_code": location.country_code or "",
            "grounding": {
                "status": location.grounding_status,
                "place_id": location.google_place_id or "",
                "google_maps_place_url": location.google_maps_place_url or "",
                "latitude": location.latitude or 0.0,
                "longitude": location.longitude or 0.0,
                "plus_code": location.plus_code or "",
                "last_error": location.grounding_last_error or "",
                "has_attribution": bool(location.google_maps_place_url),
                "attribution_label": "Google Maps" if location.google_maps_place_url else "",
            },
            "perspective": perspective or "patient",
            "cards": [self._serialize_card(card) for card in cards],
            "audit_events": [self._serialize_audit_event(event) for event in audit_events],
            "voice_session": {
                "status": "not_started",
                "label": "Browser voice will be enabled in Phase 3.",
            },
        }

    def _serialize_voice_session(self, session):
        return {
            "session_key": session.session_key,
            "state": session.state,
            "browser_status": session.browser_status or "",
            "preview_transcript": session.preview_transcript or "",
            "final_transcript": session.final_transcript or "",
            "transcript_summary": session.transcript_summary or "",
            "lead_id": session.lead_id.id if session.lead_id else False,
            "is_low_vision_mode": session.is_low_vision_mode,
            "perspective": session.perspective,
        }

    @http.route(
        "/p/<string:slug>",
        type="http",
        auth="public",
        website=True,
        methods=["GET"],
        sitemap=False,
    )
    def portalops_location_page(self, slug, **kwargs):
        location = self._get_location(slug)
        if not location:
            return request.not_found()
        perspective = kwargs.get("perspective") or "patient"
        return request.render(
            "portalops_demo.location_page",
            {
                "location": location,
                "cards": self._cards_for_perspective(location, perspective),
                "audit_events": location.audit_event_ids.sorted(key=lambda rec: (rec.sequence, rec.id)),
                "perspective": perspective,
                "google_maps_browser_api_key": self._get_google_maps_browser_api_key(),
            },
        )

    @http.route(
        "/portalops/api/location/<string:slug>",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def portalops_location_state(self, slug, **kwargs):
        location = self._get_location(slug)
        if not location:
            payload = {"error": "location_not_found", "slug": slug}
            return request.make_response(
                json.dumps(payload),
                headers=[("Content-Type", "application/json")],
                status=404,
            )
        perspective = kwargs.get("perspective") or "patient"
        payload = self._serialize_location(location, perspective=perspective)
        latest_session = request.env["portalops.demo.voice.session"].sudo().search(
            [("location_id", "=", location.id)],
            limit=1,
            order="create_date desc",
        )
        if latest_session:
            payload["voice_session"] = self._serialize_voice_session(latest_session)
        return request.make_response(
            json.dumps(payload),
            headers=[("Content-Type", "application/json")],
        )

    @http.route(
        "/portalops/api/location/<string:slug>/perspective",
        type="jsonrpc",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def portalops_location_perspective(self, slug, **kwargs):
        location = self._get_location(slug)
        if not location:
            return {"success": False, "error": "location_not_found"}
        perspective = kwargs.get("perspective") or "patient"
        return {"success": True, "state": self._serialize_location(location, perspective=perspective)}

    @http.route(
        "/portalops/api/location/<string:slug>/resolve",
        type="jsonrpc",
        auth="user",
        methods=["POST"],
    )
    def portalops_location_resolve(self, slug, **kwargs):
        result = request.env["portalops.demo.grounding.service"].sudo().resolve_location_by_slug(slug)
        return result

    @http.route(
        "/portalops/api/location/<string:slug>/voice-session/start",
        type="jsonrpc",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def portalops_voice_session_start(self, slug, **kwargs):
        location = self._get_location(slug)
        if not location:
            return {"success": False, "error": "location_not_found"}
        perspective = kwargs.get("perspective") or "patient"
        is_low_vision_mode = bool(kwargs.get("is_low_vision_mode"))
        session, widget = request.env["portalops.demo.voice.service"].sudo().start_session(
            location,
            perspective=perspective,
            is_low_vision_mode=is_low_vision_mode,
        )
        return {"success": True, "session": self._serialize_voice_session(session), "widget": widget}

    @http.route(
        "/portalops/api/location/<string:slug>/voice-session/stop",
        type="jsonrpc",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def portalops_voice_session_stop(self, slug, **kwargs):
        location = self._get_location(slug)
        if not location:
            return {"success": False, "error": "location_not_found"}
        session_key = kwargs.get("session_key")
        session = request.env["portalops.demo.voice.session"].sudo().search(
            [("location_id", "=", location.id), ("session_key", "=", session_key)],
            limit=1,
        )
        if not session:
            return {"success": False, "error": "session_not_found"}
        request.env["portalops.demo.voice.service"].sudo().mark_stopped(session)
        return {"success": True, "session": self._serialize_voice_session(session)}

    @http.route(
        "/portalops/api/location/<string:slug>/voice-session/<string:session_key>/demo-complete",
        type="jsonrpc",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def portalops_voice_session_demo_complete(self, slug, session_key, **kwargs):
        location = self._get_location(slug)
        if not location:
            return {"success": False, "error": "location_not_found"}
        session = request.env["portalops.demo.voice.session"].sudo().search(
            [("location_id", "=", location.id), ("session_key", "=", session_key)],
            limit=1,
        )
        if not session:
            return {"success": False, "error": "session_not_found"}
        transcript_text = kwargs.get("transcript") or ""
        summary = kwargs.get("summary") or ""
        request.env["portalops.demo.voice.service"].sudo().complete_demo_script(
            session,
            transcript_text=transcript_text,
            summary=summary,
        )
        return {"success": True, "session": self._serialize_voice_session(session)}

    @http.route(
        "/portalops/api/location/<string:slug>/voice-session/<string:session_key>",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def portalops_voice_session_status(self, slug, session_key, **kwargs):
        location = self._get_location(slug)
        if not location:
            return request.make_response(
                json.dumps({"success": False, "error": "location_not_found"}),
                headers=[("Content-Type", "application/json")],
                status=404,
            )
        session = request.env["portalops.demo.voice.session"].sudo().search(
            [("location_id", "=", location.id), ("session_key", "=", session_key)],
            limit=1,
        )
        if not session:
            return request.make_response(
                json.dumps({"success": False, "error": "session_not_found"}),
                headers=[("Content-Type", "application/json")],
                status=404,
            )
        return request.make_response(
            json.dumps({"success": True, "session": self._serialize_voice_session(session)}),
            headers=[("Content-Type", "application/json")],
        )

    @http.route(
        "/portalops/api/location/<string:slug>/voice-session/<string:session_key>/preview",
        type="jsonrpc",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def portalops_voice_session_preview(self, slug, session_key, **kwargs):
        location = self._get_location(slug)
        if not location:
            return {"success": False, "error": "location_not_found"}
        session = request.env["portalops.demo.voice.session"].sudo().search(
            [("location_id", "=", location.id), ("session_key", "=", session_key)],
            limit=1,
        )
        if not session:
            return {"success": False, "error": "session_not_found"}
        transcript = kwargs.get("preview_transcript") or ""
        mic_denied = bool(kwargs.get("mic_denied"))
        service = request.env["portalops.demo.voice.service"].sudo()
        if mic_denied:
            service.mark_mic_denied(session)
        else:
            service.update_preview(session, transcript)
        return {"success": True, "session": self._serialize_voice_session(session)}

    @http.route(
        "/portalops/api/location/<string:slug>/voice-session/<string:session_key>/dograh-event",
        type="jsonrpc",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def portalops_voice_session_dograh_event(self, slug, session_key, **kwargs):
        location = self._get_location(slug)
        if not location:
            return {"success": False, "error": "location_not_found"}
        session = request.env["portalops.demo.voice.session"].sudo().search(
            [("location_id", "=", location.id), ("session_key", "=", session_key)],
            limit=1,
        )
        if not session:
            return {"success": False, "error": "session_not_found"}
        event = kwargs.get("event") or ""
        run_id = kwargs.get("workflow_run_id") or kwargs.get("run_id") or ""
        service = request.env["portalops.demo.voice.service"].sudo()
        if event == "connected":
            service.mark_connected(session, run_id)
        elif event in {"disconnected", "completed"}:
            service.complete_from_run(session, run_id=run_id)
        elif event == "error":
            service.mark_failed(session, kwargs.get("message") or "Dograh browser call failed.")
        return {"success": True, "session": self._serialize_voice_session(session)}

    @http.route(
        "/portalops/api/location/<string:slug>/review-triage/trigger",
        type="jsonrpc",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def portalops_review_triage_trigger(self, slug, **kwargs):
        location = self._get_location(slug)
        if not location:
            return {"success": False, "error": "location_not_found"}
        latest_session = request.env["portalops.demo.voice.session"].sudo().search(
            [("location_id", "=", location.id)],
            limit=1,
            order="create_date desc",
        )
        draft = {
            "status": "draft",
            "reply_draft": "Thanks for reaching out. We captured your Midtown interest and a team member can follow up with next steps.",
            "crm_note": latest_session.transcript_summary if latest_session else "No voice summary yet.",
            "approval_required": True,
        }
        request.env["portalops.demo.audit_event"].sudo().create(
            {
                "location_id": location.id,
                "event_type": "review",
                "title": "Review triage drafted",
                "detail": "A draft-only follow-up packet was created for manual review.",
                "sequence": 900,
            }
        )
        return {"success": True, "draft": draft}

    @http.route(
        "/portalops/api/location/<string:slug>/browser-confirmation/trigger",
        type="jsonrpc",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def portalops_browser_confirmation_trigger(self, slug, **kwargs):
        location = self._get_location(slug)
        if not location:
            return {"success": False, "error": "location_not_found"}
        latest_session = request.env["portalops.demo.voice.session"].sudo().search(
            [("location_id", "=", location.id)],
            limit=1,
            order="create_date desc",
        )
        packet = {
            "status": "confirmation_only",
            "submitted": False,
            "banner": "Not submitted",
            "summary": latest_session.transcript_summary if latest_session else "Awaiting completed voice session.",
            "proposed_actions": [
                "Call back with Midtown availability options",
                "Send pricing and visit information",
                "Review before external submission",
            ],
        }
        request.env["portalops.demo.audit_event"].sudo().create(
            {
                "location_id": location.id,
                "event_type": "browser",
                "title": "Browser confirmation drafted",
                "detail": "A confirmation-only packet was prepared and not submitted.",
                "sequence": 910,
            }
        )
        return {"success": True, "packet": packet}

    @http.route(
        "/portalops/api/location/<string:slug>/audit",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def portalops_location_audit(self, slug, **kwargs):
        location = self._get_location(slug)
        if not location:
            return request.make_response(
                json.dumps({"success": False, "error": "location_not_found"}),
                headers=[("Content-Type", "application/json")],
                status=404,
            )
        events = location.audit_event_ids.sorted(key=lambda rec: (rec.sequence, rec.id))
        return request.make_response(
            json.dumps({"success": True, "audit_events": [self._serialize_audit_event(event) for event in events]}),
            headers=[("Content-Type", "application/json")],
        )

    @http.route(
        "/portalops/integrations/dograh/webhook",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def portalops_dograh_webhook(self, **kwargs):
        raw_body = request.httprequest.get_data(as_text=True)
        try:
            payload = json.loads(raw_body) if raw_body else {}
        except (TypeError, ValueError):
            return request.make_response(
                json.dumps({"success": False, "error": "invalid_json"}),
                headers=[("Content-Type", "application/json")],
                status=400,
            )

        expected = request.env["ir.config_parameter"].sudo().get_str("portalops_demo.dograh_webhook_secret", "")
        supplied = request.httprequest.headers.get("X-Dograh-Webhook-Secret", "")
        if expected and supplied != expected:
            return request.make_response(
                json.dumps({"success": False, "error": "invalid_secret"}),
                headers=[("Content-Type", "application/json")],
                status=403,
            )

        result = request.env["portalops.demo.voice.service"].sudo().process_webhook(payload)
        return request.make_response(
            json.dumps(result),
            headers=[("Content-Type", "application/json")],
            status=200 if result.get("success") else 404,
        )
