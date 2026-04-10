import logging

from datetime import datetime, timedelta
from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class AiAssistantServiceCrm(models.AbstractModel):
    """Extend the AI assistant service with CRM pipeline intents."""

    _inherit = "ai.assistant.service"

    # ------------------------------------------------------------------
    # Read intent handlers
    # ------------------------------------------------------------------

    def _handle_lead_lookup(self, intent_data, resolved_data, action_log=None):
        """Look up CRM leads by name, email, or phone."""
        params = intent_data.get("parameters", {})
        domain = []
        name = params.get("lead_name")
        email = params.get("email")
        phone = params.get("phone")

        if name:
            domain.append("|")
            domain.append(("contact_name", "ilike", name))
            domain.append(("partner_name", "ilike", name))
        if email:
            domain.append(("email_from", "ilike", email))
        if phone:
            domain.append("|")
            domain.append(("phone", "ilike", phone))
            domain.append(("mobile", "ilike", phone))

        if not domain:
            # No search criteria — return recent/new leads instead of an error
            from datetime import datetime, timedelta
            cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            domain = [("create_date", ">=", cutoff), ("active", "=", True)]
            leads = self.env["crm.lead"].search(domain, limit=10, order="create_date desc")
            if not leads:
                return {"success": True, "message": "No new leads in the last 30 days.", "data": []}
            data = []
            for lead in leads:
                data.append({
                    "id": lead.id,
                    "name": lead.name,
                    "contact_name": lead.contact_name,
                    "email": lead.email_from,
                    "phone": lead.phone,
                    "stage": lead.stage_id.name,
                    "score": lead.dojo_lead_score,
                    "trial_attended": lead.trial_attended,
                    "is_converted": lead.is_converted,
                })
            return {
                "success": True,
                "message": f"Found {len(data)} new lead(s) in the last 30 days.",
                "data": data,
            }

        leads = self.env["crm.lead"].search(domain, limit=10)
        if not leads:
            return {"success": True, "message": "No leads found matching the search criteria.", "data": []}

        data = []
        for lead in leads:
            data.append({
                "id": lead.id,
                "name": lead.name,
                "contact_name": lead.contact_name,
                "email": lead.email_from,
                "phone": lead.phone,
                "stage": lead.stage_id.name,
                "score": lead.dojo_lead_score,
                "trial_attended": lead.trial_attended,
                "is_converted": lead.is_converted,
            })

        return {
            "success": True,
            "message": f"Found {len(data)} lead(s).",
            "data": data,
        }

    def _handle_pipeline_summary(self, intent_data, resolved_data, action_log=None):
        """Summarise the CRM pipeline by stage."""
        stages = self.env["crm.stage"].search([], order="sequence")
        summary = []
        total = 0
        for stage in stages:
            count = self.env["crm.lead"].search_count([
                ("stage_id", "=", stage.id),
                ("active", "=", True),
            ])
            summary.append({"stage": stage.name, "count": count})
            total += count

        return {
            "success": True,
            "message": f"Pipeline has {total} active lead(s) across {len(stages)} stages.",
            "data": summary,
        }

    def _handle_trial_schedule(self, intent_data, resolved_data, action_log=None):
        """List upcoming trial bookings."""
        params = intent_data.get("parameters", {})
        date_str = params.get("date")

        domain = [
            ("trial_session_id", "!=", False),
            ("trial_attended", "=", False),
            ("trial_session_id.start_datetime", ">", fields.Datetime.now()),
        ]

        if date_str:
            try:
                target = datetime.strptime(date_str, "%Y-%m-%d")
                domain.append(("trial_session_id.start_datetime", ">=", target))
                domain.append(("trial_session_id.start_datetime", "<", target + timedelta(days=1)))
            except ValueError:
                pass

        leads = self.env["crm.lead"].search(domain, limit=20, order="trial_session_id")
        data = []
        for lead in leads:
            data.append({
                "lead": lead.contact_name or lead.partner_name or lead.name,
                "session": lead.trial_session_id.name,
                "datetime": str(lead.trial_session_id.start_datetime),
                "phone": lead.phone or "",
            })

        return {
            "success": True,
            "message": f"{len(data)} upcoming trial(s).",
            "data": data,
        }

    # ------------------------------------------------------------------
    # Write intent handlers
    # ------------------------------------------------------------------

    def _handle_lead_qualify(self, intent_data, resolved_data, action_log=None):
        """Move lead to Qualified stage and generate booking link."""
        lead = self._resolve_crm_lead(intent_data)
        if not lead:
            return {"success": False, "message": "Could not find the specified lead."}

        qualified_stage = self.env["crm.stage"].search([("name", "=", "Qualified")], limit=1)
        if not qualified_stage:
            return {"success": False, "message": "Qualified stage not found."}

        if not lead.trial_booking_token:
            lead._generate_trial_tokens()

        lead.write({"stage_id": qualified_stage.id})

        if action_log:
            self.env["dojo.ai.undo.snapshot"].create_snapshot(
                action_log.id, "crm.lead", lead.id, "write"
            )

        return {
            "success": True,
            "message": f"Lead '{lead.contact_name or lead.name}' moved to Qualified. Booking link generated.",
            "data": {"id": lead.id, "booking_url": lead.trial_booking_url},
        }

    def _handle_lead_mark_attended(self, intent_data, resolved_data, action_log=None):
        """Mark a lead's trial as attended."""
        lead = self._resolve_crm_lead(intent_data)
        if not lead:
            return {"success": False, "message": "Could not find the specified lead."}

        attended_stage = self.env["crm.stage"].search([("name", "=", "Trial Attended")], limit=1)
        if not attended_stage:
            return {"success": False, "message": "Trial Attended stage not found."}

        lead.write({
            "stage_id": attended_stage.id,
            "trial_attended": True,
        })

        if action_log:
            self.env["dojo.ai.undo.snapshot"].create_snapshot(
                action_log.id, "crm.lead", lead.id, "write"
            )

        return {
            "success": True,
            "message": f"'{lead.contact_name or lead.name}' marked as Trial Attended.",
        }

    def _handle_lead_convert(self, intent_data, resolved_data, action_log=None):
        """Convert a CRM lead to a dojo member."""
        lead = self._resolve_crm_lead(intent_data)
        if not lead:
            return {"success": False, "message": "Could not find the specified lead."}

        if lead.is_converted:
            return {
                "success": False,
                "message": f"Lead '{lead.contact_name or lead.name}' is already converted.",
            }

        try:
            lead.action_convert_to_member()
            return {
                "success": True,
                "message": f"Lead '{lead.contact_name or lead.name}' converted to member.",
                "data": {"member_id": lead.dojo_member_id.id if lead.dojo_member_id else None},
            }
        except Exception as exc:
            _logger.error("AI CRM: convert lead %s failed: %s", lead.id, exc)
            return {"success": False, "message": f"Conversion failed: {exc}"}

    def _handle_lead_create(self, intent_data, resolved_data, action_log=None):
        """Create a new CRM lead (prospect), supports batch via 'contacts' list."""
        params = intent_data.get("parameters", {}) if intent_data else {}

        # ── Batch mode: contacts list ──────────────────────────────────────
        contacts = params.get("contacts") or []
        if isinstance(contacts, list) and len(contacts) > 1:
            first_stage = self.env["crm.stage"].search([], order="sequence asc", limit=1)
            results = []
            for contact in contacts:
                name = contact.get("contact_name") or contact.get("name") or ""
                if not name:
                    results.append({"name": "Unknown", "success": False, "error": "No name provided"})
                    continue
                vals = {
                    "name": f"Trial - {name}",
                    "contact_name": name,
                    "phone": contact.get("phone", ""),
                    "email_from": contact.get("email", ""),
                }
                if first_stage:
                    vals["stage_id"] = first_stage.id
                lead = self.env["crm.lead"].create(vals)
                if action_log:
                    self.env["dojo.ai.undo.snapshot"].create_snapshot(
                        action_log.id, "crm.lead", lead.id, "create"
                    )
                results.append({"name": name, "success": True, "id": lead.id})
            success_count = sum(1 for r in results if r["success"])
            return {
                "success": success_count > 0,
                "bulk": True,
                "message": f"Created {success_count}/{len(results)} new leads.",
                "results": results,
            }

        # ── Single mode (existing behaviour) ──────────────────────────────
        contact_name = params.get("contact_name") or params.get("name")
        if not contact_name:
            return {"success": False, "message": "Please provide the prospect's name."}

        phone = params.get("phone", "")
        email = params.get("email", "")

        first_stage = self.env["crm.stage"].search([], order="sequence asc", limit=1)
        vals = {
            "name": f"Trial - {contact_name}",
            "contact_name": contact_name,
            "phone": phone,
            "email_from": email,
        }
        if first_stage:
            vals["stage_id"] = first_stage.id

        lead = self.env["crm.lead"].create(vals)

        if action_log:
            self.env["dojo.ai.undo.snapshot"].create_snapshot(
                action_log.id, "crm.lead", lead.id, "create"
            )

        return {
            "success": True,
            "message": f"New prospect '{contact_name}' added to the pipeline.",
            "data": {"id": lead.id, "name": lead.name},
        }

    def _handle_lead_mark_lost(self, intent_data, resolved_data, action_log=None):
        """Mark a CRM lead as lost."""
        lead = self._resolve_crm_lead(intent_data)
        if not lead:
            return {"success": False, "message": "Could not find the specified lead."}

        lead.action_set_lost()
        return {
            "success": True,
            "message": f"Lead '{lead.contact_name or lead.name}' marked as lost.",
        }

    def _handle_lead_mark_won(self, intent_data, resolved_data, action_log=None):
        """Mark a CRM lead as won."""
        lead = self._resolve_crm_lead(intent_data)
        if not lead:
            return {"success": False, "message": "Could not find the specified lead."}

        lead.action_set_won()
        return {
            "success": True,
            "message": f"Lead '{lead.contact_name or lead.name}' marked as won.",
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_crm_lead(self, intent_data):
        """Resolve a CRM lead from intent parameters (by ID or name)."""
        params = intent_data.get("parameters", {})
        lead_id = params.get("lead_id")
        lead_name = params.get("lead_name")

        if lead_id:
            lead = self.env["crm.lead"].browse(int(lead_id)).exists()
            if lead:
                return lead

        if lead_name:
            lead = self.env["crm.lead"].search(
                ["|", ("contact_name", "ilike", lead_name), ("partner_name", "ilike", lead_name)],
                limit=1,
            )
            if lead:
                return lead

        return None
