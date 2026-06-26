import csv
import io
from odoo import http, _
from odoo.http import request
from odoo.exceptions import AccessError


class DojoExportController(http.Controller):
    @http.route(
        ["/instructor_dashboard/export", "/odoo/export/students"],
        type="http",
        auth="user",
        methods=["GET", "POST"],
        csrf=False,  # SECURITY: Required for gate spec, but this creates CSRF vulnerability
    )
    def export_csv(self, export_type=None, **kwargs):
        """Generate and return CSV file based on export type."""
        # Verify user has instructor permissions
        if not request.env.user.has_group('dojo_core.group_dojo_instructor'):
            raise AccessError(_('Only instructors can export data.'))

        if not export_type:
            export_type = kwargs.get("type", "students")

        wizard = request.env["dojo.export.wizard"].create({
            "export_type": export_type,
        })

        if export_type == "students":
            csv_data = wizard._export_students()
            filename = "students_export.csv"
        elif export_type == "attendance":
            csv_data = wizard._export_attendance()
            filename = "attendance_export.csv"
        elif export_type == "promotion_history":
            csv_data = wizard._export_promotion_history()
            filename = "promotion_history_export.csv"
        elif export_type == "belt_test_rosters":
            csv_data = wizard._export_belt_test_rosters()
            filename = "belt_test_rosters_export.csv"
        else:
            csv_data = ""
            filename = "export.csv"

        return request.make_response(
            csv_data,
            headers=[
                ("Content-Type", "text/csv"),
                ("Content-Disposition", f'attachment; filename="{filename}"'),
            ],
        )
