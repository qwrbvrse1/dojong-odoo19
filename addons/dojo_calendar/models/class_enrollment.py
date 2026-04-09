from odoo import api, models


class DojoClassEnrollmentCalendar(models.Model):
    _inherit = "dojo.class.enrollment"

    def _sync_session_calendar(self):
        """Re-sync calendar attendees for affected sessions."""
        sessions = self.mapped("session_id").filtered("calendar_event_id")
        if sessions:
            sessions.with_context(no_mail_for_attendees=True)._sync_calendar_event()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_session_calendar()
        return records

    def write(self, vals):
        result = super().write(vals)
        if "status" in vals or "member_id" in vals:
            self._sync_session_calendar()
        return result

    def unlink(self):
        sessions = self.mapped("session_id").filtered("calendar_event_id")
        result = super().unlink()
        if sessions:
            sessions.with_context(no_mail_for_attendees=True)._sync_calendar_event()
        return result
