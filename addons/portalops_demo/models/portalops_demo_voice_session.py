import uuid

from odoo import fields, models
from odoo.exceptions import UserError


class PortalOpsDemoVoiceSession(models.Model):
    _name = "portalops.demo.voice.session"
    _description = "PortalOps Demo Voice Session"
    _order = "create_date desc, id desc"

    name = fields.Char(required=True, default=lambda self: "PortalOps Demo Voice Session")
    session_key = fields.Char(
        required=True,
        copy=False,
        index=True,
        default=lambda self: uuid.uuid4().hex,
    )
    external_session_key = fields.Char(copy=False, index=True)
    location_id = fields.Many2one(
        "portalops.demo.location",
        required=True,
        ondelete="cascade",
    )
    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("active", "Active"),
            ("stopped", "Stopped"),
            ("completed", "Completed"),
            ("failed", "Failed"),
            ("mic_denied", "Mic Denied"),
        ],
        default="pending",
        required=True,
    )
    perspective = fields.Selection(
        [
            ("doctor", "Doctor"),
            ("nurse", "Nurse"),
            ("patient", "Patient"),
            ("customer", "Customer"),
            ("sales", "Sales"),
            ("manager", "Manager"),
        ],
        default="patient",
        required=True,
    )
    is_low_vision_mode = fields.Boolean(default=False)
    provider = fields.Char(default="dograh")
    provider_run_id = fields.Char(copy=False)
    preview_transcript = fields.Text()
    final_transcript = fields.Text()
    transcript_summary = fields.Text()
    browser_status = fields.Char()
    lead_id = fields.Many2one("crm.lead", ondelete="set null")
    error_message = fields.Text()
    started_at = fields.Datetime(default=fields.Datetime.now)
    stopped_at = fields.Datetime()
    completed_at = fields.Datetime()

    def action_view_lead(self):
        self.ensure_one()
        if not self.lead_id:
            raise UserError("This voice session does not have a CRM lead yet.")
        return {
            "type": "ir.actions.act_window",
            "name": "CRM Lead",
            "res_model": "crm.lead",
            "res_id": self.lead_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_trigger_test_webhook(self):
        service = self.env["portalops.demo.voice.service"].sudo()
        for session in self:
            payload = {
                "sessionKey": session.session_key,
                "qualified": True,
                "outcome": "qualified",
                "summary": f"Internal test webhook for {session.location_id.name}.",
                "contact": {
                    "name": "PortalOps Test Prospect",
                    "phone": "4045550101",
                    "email": "portalops.test@example.com",
                },
                "transcript": [
                    {"role": "user", "message": "I want pricing and follow-up details."},
                    {"role": "assistant", "message": "I can capture that and create a follow-up lead."},
                ],
            }
            service.process_webhook(payload)
        return True
