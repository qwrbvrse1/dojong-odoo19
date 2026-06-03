import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request

from odoo import fields, models

_logger = logging.getLogger(__name__)


class PortalOpsDemoVoiceService(models.AbstractModel):
    _name = "portalops.demo.voice.service"
    _description = "PortalOps Demo Voice Service"

    def _config(self):
        icp = self.env["ir.config_parameter"].sudo()
        return {
            "api_key": icp.get_str("portalops_demo.dograh_api_key", ""),
            "api_base_url": icp.get_str("portalops_demo.dograh_api_base_url", "http://dograh-api:8000/api/v1"),
            "api_public_base_url": icp.get_str("portalops_demo.dograh_start_url", "http://127.0.0.1:8000"),
            "ui_base_url": icp.get_str("portalops_demo.dograh_ui_base_url", "http://127.0.0.1:3010"),
            "auth_email": icp.get_str("portalops_demo.dograh_auth_email", "portalops-demo@example.com"),
            "auth_password": icp.get_str("portalops_demo.dograh_auth_password", "PortalOpsDemo123!"),
            "webhook_secret": icp.get_str("portalops_demo.dograh_webhook_secret", ""),
            "workflow_id": icp.get_str("portalops_demo.dograh_flow_id", ""),
            "low_vision_workflow_id": icp.get_str("portalops_demo.dograh_low_vision_flow_id", ""),
            "embed_token": icp.get_str("portalops_demo.dograh_embed_token", ""),
            "base_url": icp.get_str("web.base.url", ""),
        }

    def _set_config(self, key, value):
        icp = self.env["ir.config_parameter"].sudo()
        record = icp.search([("key", "=", key)], limit=1)
        if record:
            record.value = value or ""
        else:
            icp.create({"key": key, "value": value or ""})

    def _create_audit_event(self, location, event_type, title, detail):
        self.env["portalops.demo.audit_event"].sudo().create(
            {
                "location_id": location.id,
                "event_type": event_type,
                "title": title,
                "detail": detail,
                "sequence": 100 + location.audit_event_ids.search_count([("location_id", "=", location.id)]) * 10,
            }
        )

    def _dograh_request(self, path, payload=None, token="", method="GET", absolute=False):
        config = self._config()
        url = path if absolute else f"{config['api_base_url'].rstrip('/')}/{path.lstrip('/')}"
        headers = {"Accept": "application/json"}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8") if payload is not None else None,
            headers=headers,
            method=method,
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            body = response.read().decode("utf-8")
        return json.loads(body) if body else {}

    def _dograh_auth_token(self):
        config = self._config()
        auth_payload = {
            "email": config["auth_email"],
            "password": config["auth_password"],
            "name": "PortalOps Demo",
        }
        try:
            result = self._dograh_request("auth/login", {"email": auth_payload["email"], "password": auth_payload["password"]}, method="POST")
            return result.get("token", "")
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise
        try:
            result = self._dograh_request("auth/signup", auth_payload, method="POST")
            return result.get("token", "")
        except urllib.error.HTTPError:
            result = self._dograh_request("auth/login", {"email": auth_payload["email"], "password": auth_payload["password"]}, method="POST")
            return result.get("token", "")

    def ensure_embed_config(self):
        config = self._config()
        if config["workflow_id"] and config["embed_token"]:
            return {
                "workflow_id": config["workflow_id"],
                "embed_token": config["embed_token"],
            }

        token = self._dograh_auth_token()
        workflow = self._dograh_request(
            "workflow/create/template",
            {
                "call_type": "inbound",
                "use_case": "Atlanta Midtown investor demo intake",
                "activity_description": (
                    "Greet the caller for the Atlanta Midtown PlaceTwin investor demo, collect their name, phone, "
                    "email, moving or purchase timeline, and what property or care-related need they have. Keep the "
                    "tone warm and concise. Mark the outcome qualified when they provide contact details and a concrete "
                    "need. End with a short confirmation recap."
                ),
            },
            token=token,
            method="POST",
        )
        workflow_id = str(workflow.get("id") or "")
        if not workflow_id:
            raise ValueError("Dograh workflow bootstrap did not return a workflow id.")

        embed = self._dograh_request(
            f"workflow/{workflow_id}/embed-token",
            {
                "allowed_domains": ["localhost", "127.0.0.1"],
                "settings": {
                    "embedMode": "headless",
                    "theme": "light",
                    "buttonText": "Start Midtown Voice Intake",
                    "autoStart": False,
                },
                "expires_in_days": 30,
            },
            token=token,
            method="POST",
        )
        embed_token = embed.get("token", "")
        self._set_config("portalops_demo.dograh_flow_id", workflow_id)
        self._set_config("portalops_demo.dograh_low_vision_flow_id", workflow_id)
        self._set_config("portalops_demo.dograh_embed_token", embed_token)
        return {"workflow_id": workflow_id, "embed_token": embed_token}

    def get_widget_payload(self, is_low_vision_mode=False):
        config = self._config()
        embed = self.ensure_embed_config()
        workflow_id = config["low_vision_workflow_id"] if is_low_vision_mode and config["low_vision_workflow_id"] else embed["workflow_id"]
        return {
            "token": embed["embed_token"],
            "workflow_id": workflow_id,
            "script_url": "/portalops_demo/static/src/vendor/dograh-widget.js",
            "api_endpoint": config["api_public_base_url"].rstrip("/"),
            "environment": "local",
        }

    def start_session(self, location, perspective="patient", is_low_vision_mode=False):
        session = self.env["portalops.demo.voice.session"].sudo().create(
            {
                "name": f"{location.name} Voice Session",
                "location_id": location.id,
                "perspective": perspective or "patient",
                "is_low_vision_mode": bool(is_low_vision_mode),
                "state": "pending",
                "browser_status": "Preparing browser voice demo",
            }
        )
        session.write(
            {
                "state": "active",
                "browser_status": "Browser voice demo ready",
            }
        )
        self._create_audit_event(location, "voice", "Voice session started", "Browser voice demo session initialized.")
        return session, {"mode": "scripted_browser_demo"}

    def mark_stopped(self, session):
        session.sudo().write(
            {
                "state": "stopped" if session.state not in ("completed", "failed") else session.state,
                "stopped_at": fields.Datetime.now(),
                "browser_status": "Stopped from browser",
            }
        )
        self._create_audit_event(session.location_id, "voice", "Voice session stopped", "Browser voice session was manually stopped.")
        return session

    def mark_connected(self, session, run_id):
        session.sudo().write(
            {
                "state": "active",
                "provider_run_id": str(run_id or ""),
                "browser_status": "Dograh call connected",
            }
        )
        self._create_audit_event(
            session.location_id,
            "voice",
            "Dograh call connected",
            f"Workflow run {run_id} connected for browser voice intake.",
        )
        return session

    def mark_failed(self, session, message):
        session.sudo().write(
            {
                "state": "failed",
                "error_message": message,
                "browser_status": message,
                "completed_at": fields.Datetime.now(),
            }
        )
        self._create_audit_event(session.location_id, "voice", "Voice session failed", message)
        return session

    def mark_mic_denied(self, session):
        session.sudo().write({"state": "mic_denied", "browser_status": "Microphone permission denied"})
        self._create_audit_event(session.location_id, "voice", "Microphone denied", "User denied browser microphone access.")

    def update_preview(self, session, transcript):
        session.sudo().write({"preview_transcript": transcript or "", "browser_status": "Preview transcript updated"})

    def complete_demo_script(self, session, transcript_text="", summary=""):
        session.sudo().write(
            {
                "final_transcript": transcript_text or session.final_transcript or session.preview_transcript or "",
                "transcript_summary": summary or "Scripted role demo completed.",
                "completed_at": fields.Datetime.now(),
                "state": "completed",
                "browser_status": "Scripted demo completed",
            }
        )
        self._create_audit_event(
            session.location_id,
            "voice",
            "Scripted voice demo completed",
            summary or f"{session.perspective.title()} demo conversation completed in browser.",
        )
        return session

    def _fetch_transcript(self, transcript_url):
        if not transcript_url:
            return ""
        internal_url = transcript_url.replace("http://localhost:9000", "http://dograh-minio:9000")
        req = urllib.request.Request(internal_url, headers={"Accept": "text/plain"}, method="GET")
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.read().decode("utf-8")

    def _contact_from_context(self, context):
        text_blob = json.dumps(context or {})
        email_match = re.search(r"([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})", text_blob, re.I)
        phone_match = re.search(r"(\+?1?[\s\-.(]*\d{3}[\s\-.)(]*\d{3}[\s\-.]*\d{4})", text_blob)
        return {
            "name": (context or {}).get("name") or (context or {}).get("customer_name") or "",
            "email": email_match.group(1) if email_match else "",
            "phone": phone_match.group(1) if phone_match else "",
        }

    def _derive_summary(self, gathered_context, transcript):
        if gathered_context:
            pieces = []
            for key, value in gathered_context.items():
                if value in (False, None, "", [], {}):
                    continue
                label = key.replace("_", " ").strip().title()
                pieces.append(f"{label}: {value}")
            if pieces:
                return " | ".join(pieces)[:500]
        return (transcript or "Browser voice call completed through Dograh.").strip()[:500]

    def _is_qualified(self, contact, transcript, gathered_context):
        transcript_text = (transcript or "").lower()
        need_keywords = [
            "need",
            "timeline",
            "move",
            "moving",
            "property",
            "apartment",
            "care",
            "pricing",
            "tour",
            "availability",
        ]
        has_contact = bool(contact.get("email") or contact.get("phone"))
        has_need = any(keyword in transcript_text for keyword in need_keywords) or bool(gathered_context)
        return has_contact and has_need

    def _find_or_create_lead(self, session, summary, transcript_text, contact_name="", phone="", email=""):
        Lead = self.env["crm.lead"].sudo()
        medium = self.env.ref("dojo_connect_ai.utm_medium_voice_ai", raise_if_not_found=False)
        tag_voice = self.env.ref("dojo_connect_ai.crm_tag_voice_inquiry", raise_if_not_found=False)
        stage_new = self.env.ref("dojo_crm.crm_stage_new_lead", raise_if_not_found=False)

        lead_vals = {
            "name": f"PlaceTwin Voice — {session.location_id.name}",
            "contact_name": contact_name or session.location_id.name,
            "phone": phone or False,
            "email_from": email or False,
            "description": summary or "Qualified browser voice intake",
            "portalops_demo_location_id": session.location_id.id,
            "portalops_demo_session_key": session.session_key,
            "portalops_demo_transcript_summary": summary or "",
        }
        if medium:
            lead_vals["medium_id"] = medium.id
        if stage_new:
            lead_vals["stage_id"] = stage_new.id
        if tag_voice:
            lead_vals["tag_ids"] = [(6, 0, [tag_voice.id])]

        lead = Lead.create(lead_vals)
        if transcript_text:
            lead.message_post(
                body=f"<p><strong>PortalOps Demo Voice Transcript:</strong></p><pre>{transcript_text}</pre>",
                subject="PortalOps Demo Voice Intake",
                message_type="comment",
                subtype_xmlid="mail.mt_note",
            )
        return lead

    def complete_from_run(self, session, run_id=None):
        config = self._config()
        workflow_id = config["low_vision_workflow_id"] if session.is_low_vision_mode and config["low_vision_workflow_id"] else config["workflow_id"]
        run_id = str(run_id or session.provider_run_id or "")
        if not workflow_id or not run_id:
            return self.mark_failed(session, "Dograh completion did not include a workflow run id.")

        token = self._dograh_auth_token()
        result = self._dograh_request(f"workflow/{workflow_id}/runs/{run_id}", token=token, method="GET")
        transcript_text = self._fetch_transcript(result.get("transcript_url") or "")
        gathered_context = result.get("gathered_context") or {}
        contact = self._contact_from_context(gathered_context)
        summary = self._derive_summary(gathered_context, transcript_text)
        qualified = self._is_qualified(contact, transcript_text, gathered_context)

        session.sudo().write(
            {
                "provider_run_id": run_id,
                "external_session_key": str(result.get("id") or run_id),
                "final_transcript": transcript_text,
                "transcript_summary": summary,
                "completed_at": fields.Datetime.now(),
                "state": "completed",
                "browser_status": "Completed" if result.get("is_completed") else "Call ended",
            }
        )
        self._create_audit_event(
            session.location_id,
            "voice",
            "Dograh run completed",
            f"Workflow run {run_id} completed and transcript was synchronized into Odoo.",
        )

        if qualified:
            lead = self._find_or_create_lead(
                session,
                summary,
                transcript_text,
                contact_name=contact.get("name", ""),
                phone=contact.get("phone", ""),
                email=contact.get("email", ""),
            )
            session.sudo().write({"lead_id": lead.id})
            self._create_audit_event(
                session.location_id,
                "crm",
                "CRM lead created",
                f"Lead {lead.display_name} created from qualified Dograh browser intake.",
            )
        else:
            self._create_audit_event(
                session.location_id,
                "voice",
                "Voice outcome recorded",
                "Dograh browser intake completed without meeting the default qualified-lead rule.",
            )
        return session

    def process_webhook(self, payload):
        session_key = payload.get("sessionKey") or payload.get("session_key") or payload.get("externalSessionKey")
        session = self.env["portalops.demo.voice.session"].sudo().search(
            ["|", ("session_key", "=", session_key), ("external_session_key", "=", session_key)],
            limit=1,
        )
        if not session:
            return {"success": False, "error": "session_not_found"}

        transcript_items = payload.get("transcript") or []
        if isinstance(transcript_items, list):
            final_transcript = "\n".join(
                f"{(item.get('role') or 'speaker').capitalize()}: {item.get('message') or item.get('text') or ''}".strip()
                for item in transcript_items
                if item.get("message") or item.get("text")
            )
        else:
            final_transcript = payload.get("finalTranscript") or payload.get("transcriptText") or ""

        summary = (
            payload.get("summary")
            or payload.get("analysis", {}).get("summary")
            or payload.get("qualifiedSummary")
            or ""
        )
        outcome = (payload.get("outcome") or payload.get("status") or "").lower()
        qualified = bool(payload.get("qualified")) or outcome in {"qualified", "completed", "success"}
        contact = payload.get("contact") or {}

        session.write(
            {
                "final_transcript": final_transcript,
                "transcript_summary": summary,
                "external_session_key": payload.get("externalSessionKey") or session.external_session_key,
                "provider_run_id": payload.get("runId") or session.provider_run_id,
                "completed_at": fields.Datetime.now(),
                "state": "completed" if qualified else "failed",
                "browser_status": "Completed" if qualified else "Completed without qualified outcome",
                "error_message": payload.get("errorMessage") or False,
            }
        )

        self._create_audit_event(
            session.location_id,
            "voice",
            "Voice webhook received",
            summary or "Dograh callback processed for browser voice session.",
        )

        if qualified:
            lead = self._find_or_create_lead(
                session,
                summary,
                final_transcript,
                contact_name=contact.get("name", ""),
                phone=contact.get("phone", ""),
                email=contact.get("email", ""),
            )
            session.write({"lead_id": lead.id})
            self._create_audit_event(
                session.location_id,
                "crm",
                "CRM lead created",
                f"Lead {lead.display_name} created from qualified browser voice intake.",
            )

        return {"success": True, "session_key": session.session_key, "lead_id": session.lead_id.id if session.lead_id else False}
