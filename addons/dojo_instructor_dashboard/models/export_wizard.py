import csv
import io
from odoo import fields, models, _


class DojoExportWizard(models.TransientModel):
    _name = "dojo.export.wizard"
    _description = "Dojo Data Export Wizard"

    export_type = fields.Selection(
        [
            ("students", "Students (All Fields)"),
            ("attendance", "Attendance Log"),
            ("promotion_history", "Promotion History"),
            ("belt_test_rosters", "Belt Test Rosters"),
        ],
        string="Export Type",
        required=True,
        default="students",
    )

    def action_export_csv(self):
        """Generate CSV export based on selected type and trigger download."""
        self.ensure_one()

        if self.export_type == "students":
            data = self._export_students()
            filename = "students_export.csv"
        elif self.export_type == "attendance":
            data = self._export_attendance()
            filename = "attendance_export.csv"
        elif self.export_type == "promotion_history":
            data = self._export_promotion_history()
            filename = "promotion_history_export.csv"
        elif self.export_type == "belt_test_rosters":
            data = self._export_belt_test_rosters()
            filename = "belt_test_rosters_export.csv"
        else:
            data = ""
            filename = "export.csv"

        return {
            "type": "ir.actions.act_url",
            "url": f"/instructor_dashboard/export?type={self.export_type}",
            "target": "self",
        }

    def _export_students(self):
        """Export all student fields."""
        members = self.env["dojo.member"].search([])

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "Member Number",
            "Name",
            "First Name",
            "Last Name",
            "Email",
            "Phone",
            "Date of Birth",
            "Gender",
            "Membership State",
            "Current Belt",
            "Membership Expiry",
            "Emergency Contact",
            "Blood Type",
            "Allergies",
            "Medical Notes",
            "Total Sessions",
            "Attendance Rate",
        ])

        # Data rows
        for member in members:
            emergency_contacts = ", ".join(
                f"{ec.name} ({ec.relationship}): {ec.phone}"
                for ec in member.emergency_contact_ids
            )
            writer.writerow([
                member.member_number or "",
                member.name or "",
                member.first_name or "",
                member.last_name or "",
                member.email or "",
                member.phone or "",
                member.date_of_birth.strftime("%Y-%m-%d") if member.date_of_birth else "",
                dict(member._fields["gender"].selection).get(member.gender, "") if member.gender else "",
                dict(member._fields["membership_state"].selection).get(member.membership_state, ""),
                member.current_rank_id.name if member.current_rank_id else "",
                member.expdate.strftime("%Y-%m-%d") if member.expdate else "",
                emergency_contacts,
                member.blood_type or "",
                member.allergies or "",
                member.medical_notes or "",
                member.total_sessions,
                f"{member.attendance_rate:.2f}",
            ])

        return output.getvalue()

    def _export_attendance(self):
        """Export attendance log."""
        logs = self.env["dojo.attendance.log"].search([], order="checkin_datetime desc")

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "Date",
            "Member Number",
            "Member Name",
            "Session",
            "Status",
            "Check-in Time",
            "Check-out Time",
            "Duration (Hours)",
            "Performance Rating",
            "Notes",
        ])

        # Data rows
        for log in logs:
            writer.writerow([
                log.checkin_datetime.strftime("%Y-%m-%d") if log.checkin_datetime else "",
                log.member_id.member_number or "",
                log.member_id.name or "",
                log.session_id.display_name or log.session_id.name or "",
                dict(log._fields["status"].selection).get(log.status, ""),
                log.checkin_datetime.strftime("%Y-%m-%d %H:%M:%S") if log.checkin_datetime else "",
                log.checkout_datetime.strftime("%Y-%m-%d %H:%M:%S") if log.checkout_datetime else "",
                f"{log.duration_hours:.2f}",
                dict(log._fields["performance_rating"].selection).get(log.performance_rating, "") if log.performance_rating else "",
                log.note or "",
            ])

        return output.getvalue()

    def _export_promotion_history(self):
        """Export belt promotion history."""
        ranks = self.env["dojo.member.rank"].search([], order="date_awarded desc")

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "Date Awarded",
            "Member Number",
            "Member Name",
            "Belt Rank",
            "Stripes",
            "Program",
            "Awarded By",
            "Notes",
        ])

        # Data rows
        for rank in ranks:
            writer.writerow([
                rank.date_awarded.strftime("%Y-%m-%d") if rank.date_awarded else "",
                rank.member_id.member_number or "",
                rank.member_id.name or "",
                rank.rank_id.name if rank.rank_id else "",
                rank.stripe_count,
                rank.program_id.name if rank.program_id else "",
                rank.awarded_by.name if rank.awarded_by else "",
                rank.notes or "",
            ])

        return output.getvalue()

    def _export_belt_test_rosters(self):
        """Export belt test rosters."""
        tests = self.env["dojo.belt.test"].search([], order="test_date desc")

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "Test Date",
            "Test Name",
            "Location",
            "Program",
            "Lead Instructor",
            "Status",
            "Member Number",
            "Member Name",
            "Current Belt",
            "Testing For",
            "Registration Status",
            "Result",
        ])

        # Data rows
        for test in tests:
            for registration in test.registration_ids:
                writer.writerow([
                    test.test_date.strftime("%Y-%m-%d") if test.test_date else "",
                    test.name or "",
                    test.location or "",
                    test.program_id.name if test.program_id else "",
                    test.instructor_profile_id.name if test.instructor_profile_id else "",
                    dict(test._fields["state"].selection).get(test.state, ""),
                    registration.member_id.member_number if registration.member_id else "",
                    registration.member_id.name if registration.member_id else "",
                    registration.current_rank_id.name if registration.current_rank_id else "",
                    registration.testing_for_rank_id.name if registration.testing_for_rank_id else "",
                    dict(registration._fields["status"].selection).get(registration.status, "") if hasattr(registration, "status") else "",
                    dict(registration._fields["result"].selection).get(registration.result, "") if hasattr(registration, "result") else "",
                ])

        return output.getvalue()
