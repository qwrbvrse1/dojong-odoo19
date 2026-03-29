"""
CRM Lead → Instructor Todo glue.

Creates instructor ``project.task`` todos when a CRM lead moves
through trial-related pipeline stages.
"""

from datetime import timedelta

from markupsafe import Markup

from odoo import api, fields, models

# Mirror stage name constants from crm_lead.py
_CRM_STAGE_TRIAL_BOOKED = "Trial Booked"
_CRM_STAGE_TRIAL_IN_PROGRESS = "Trial-in-progress"


class CrmLeadInstructorTodos(models.Model):
    _inherit = "crm.lead"

    def _get_trial_instructor_users(self):
        """Return the ``res.users`` for the trial session's instructor."""
        self.ensure_one()
        session = self.trial_session_id
        if session and session.instructor_profile_id and session.instructor_profile_id.user_id:
            return session.instructor_profile_id.user_id
        profiles = self.env["dojo.instructor.profile"].search([
            ("company_id", "in", [self.company_id.id, False]),
            ("user_id", "!=", False),
        ])
        return profiles.mapped("user_id")

    def _on_stage_change(self, old_stage, new_stage):
        super()._on_stage_change(old_stage, new_stage)
        users = self._get_trial_instructor_users()
        if not users:
            return
        MemberModel = self.env["dojo.member"]
        today = fields.Date.today()
        lead_name = self.contact_name or self.partner_name or "Lead"

        if new_stage == _CRM_STAGE_TRIAL_BOOKED:
            session = self.trial_session_id
            session_label = f" — {session.name}" if session else ""
            deadline = (
                session.start_datetime.date()
                if session and session.start_datetime
                else today + timedelta(days=1)
            )
            MemberModel._create_instructor_todo(
                users,
                "📅 Incoming trial: %s%s" % (lead_name, session_label),
                deadline=deadline,
                description=Markup(
                    "<p>A trial class has been booked for <strong>{name}</strong>. "
                    "Prepare a warm welcome and be ready to answer any questions.</p>"
                ).format(name=lead_name),
            )
        elif new_stage == _CRM_STAGE_TRIAL_IN_PROGRESS:
            MemberModel._create_instructor_todo(
                users,
                "🥋 Trial attended: %s — follow up to convert" % lead_name,
                deadline=today + timedelta(days=1),
                description=Markup(
                    "<p><strong>{name}</strong> attended their trial class. "
                    "Follow up to answer questions and help them choose a membership.</p>"
                ).format(name=lead_name),
            )

    def write(self, vals):
        newly_no_show = (
            self.filtered(lambda r: not r.no_show)
            if vals.get("no_show") is True
            else self.env["crm.lead"]
        )
        result = super().write(vals)
        for lead in newly_no_show:
            users = lead._get_trial_instructor_users()
            if not users:
                continue
            lead_name = lead.contact_name or lead.partner_name or "Lead"
            session_info = " (%s)" % lead.trial_session_id.name if lead.trial_session_id else ""
            self.env["dojo.member"]._create_instructor_todo(
                users,
                "❌ Trial no-show: %s%s — reach out to reschedule" % (lead_name, session_info),
                deadline=fields.Date.today() + timedelta(days=1),
                description=Markup(
                    "<p><strong>{name}</strong> did not show up for their trial class{session}. "
                    "Contact them to reschedule and keep the engagement alive.</p>"
                ).format(name=lead_name, session=session_info),
            )
        return result
