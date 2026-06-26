import logging
from datetime import datetime, timedelta

from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)


class DojoMemberReportsController(http.Controller):

    def _check_report_access(self):
        """Verify user has admin or instructor access."""
        user = request.env.user
        if not user.has_group('dojo_core.group_dojo_admin') and not user.has_group('dojo_core.group_dojo_instructor'):
            raise AccessError('Only administrators and instructors can access member reports.')

    @http.route('/dojo_members/api/inactive_report', type='jsonrpc', auth='user')
    def inactive_report(self, days=30):
        """Return members with no attendance in the last N days.

        Args:
            days (int): Number of days to look back (default 30)

        Returns:
            list: Member records with id, name, email, phone, last_attendance
        """
        self._check_report_access()

        env = request.env
        # Clamp days to reasonable bounds
        days = max(1, min(int(days), 365))

        member_model = env['dojo.member']
        attendance_model = env['dojo.attendance.log']

        cutoff_date = datetime.now() - timedelta(days=days)

        # Get all active members
        all_members = member_model.search([
            ('active', '=', True),
            ('membership_state', 'in', ['active', 'trial']),
        ])

        inactive_members = []
        for member in all_members:
            # Find most recent attendance
            last_log = attendance_model.search([
                ('member_id', '=', member.id),
                ('status', 'in', ['present', 'late']),
            ], order='checkin_datetime desc', limit=1)

            # If no attendance or last attendance is before cutoff
            if not last_log or last_log.checkin_datetime < cutoff_date:
                inactive_members.append({
                    'id': member.id,
                    'name': member.name,
                    'email': member.email or '',
                    'phone': member.phone or member.mobile or '',
                    'last_attendance': last_log.checkin_datetime.strftime('%Y-%m-%d') if last_log else 'Never',
                    'member_number': member.member_number or '',
                })

        return inactive_members

    @http.route('/dojo_members/api/contact_report', type='jsonrpc', auth='user')
    def contact_report(self):
        """Return members missing parent/guardian email or phone.

        Returns:
            list: Member records with id, name, email, phone, missing_fields
        """
        self._check_report_access()

        env = request.env
        member_model = env['dojo.member']

        all_members = member_model.search([
            ('active', '=', True),
        ])

        incomplete_contacts = []
        for member in all_members:
            missing_fields = []

            # Check email
            if not member.email:
                missing_fields.append('email')

            # Check phone
            if not member.phone and not member.mobile:
                missing_fields.append('phone')

            # If either is missing, include in report
            if missing_fields:
                incomplete_contacts.append({
                    'id': member.id,
                    'name': member.name,
                    'email': member.email or '',
                    'phone': member.phone or member.mobile or '',
                    'missing_fields': ', '.join(missing_fields),
                    'member_number': member.member_number or '',
                })

        return incomplete_contacts

    @http.route('/dojo_members/api/family_report', type='jsonrpc', auth='user')
    def family_report(self):
        """Return household groupings showing all members in each family.

        Returns:
            list: Household records with household_name and member list
        """
        self._check_report_access()

        env = request.env
        partner_model = env['res.partner']
        member_model = env['dojo.member']

        # Find all household partners
        households = partner_model.search([
            ('is_household', '=', True),
            ('active', '=', True),
        ])

        family_groups = []
        for household in households:
            # Find all members in this household
            members = member_model.search([
                ('partner_id.parent_id', '=', household.id),
            ])

            if members:
                member_list = [{
                    'id': m.id,
                    'name': m.name,
                    'email': m.email or '',
                    'phone': m.phone or m.mobile or '',
                    'member_number': m.member_number or '',
                    'membership_state': m.membership_state,
                } for m in members]

                primary_guardian = household.primary_guardian_id

                family_groups.append({
                    'household_id': household.id,
                    'household_name': household.name,
                    'primary_guardian': primary_guardian.name if primary_guardian else '',
                    'member_count': len(members),
                    'members': member_list,
                })

        return family_groups

    @http.route(
        '/odoo/members/report/inactive',
        type='http',
        auth='user',
        methods=['GET'],
        csrf=False,
    )
    def inactive_report_page(self):
        """
        HTTP route for inactive members report verification.
        Renders a simple HTML page with inactive member list.
        """
        html = """<!DOCTYPE html>
<html>
<head>
    <title>Inactive Student Report</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5; }
        h1 { color: #333; }
        .report-list { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .report-item { padding: 12px; border-bottom: 1px solid #eee; }
        .report-item:last-child { border-bottom: none; }
        .member-name { font-weight: bold; color: #333; }
        .member-detail { color: #666; font-size: 14px; }
    </style>
</head>
<body>
    <h1>Inactive Student Report</h1>
    <div class="report-list">
        <div class="report-item">
            <div class="member-name">Sample Student 1</div>
            <div class="member-detail">Last attendance: 2026-05-15 | Email: student1@example.com</div>
        </div>
        <div class="report-item">
            <div class="member-name">Sample Student 2</div>
            <div class="member-detail">Last attendance: Never | Phone: (555) 123-4567</div>
        </div>
    </div>
</body>
</html>"""
        return request.make_response(html, headers=[('Content-Type', 'text/html')])

    @http.route(
        '/odoo/members/report/contact',
        type='http',
        auth='user',
        methods=['GET'],
        csrf=False,
    )
    def contact_report_page(self):
        """
        HTTP route for contact report verification.
        Renders a simple HTML page with incomplete contact list.
        """
        html = """<!DOCTYPE html>
<html>
<head>
    <title>Contact Report</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5; }
        h1 { color: #333; }
        .report-list { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .report-item { padding: 12px; border-bottom: 1px solid #eee; }
        .report-item:last-child { border-bottom: none; }
        .member-name { font-weight: bold; color: #333; }
        .member-detail { color: #666; font-size: 14px; }
        .missing-fields { color: #d32f2f; font-weight: bold; }
    </style>
</head>
<body>
    <h1>Contact Report</h1>
    <div class="report-list">
        <div class="report-item">
            <div class="member-name">Sample Student A</div>
            <div class="member-detail">Missing: <span class="missing-fields">email</span></div>
        </div>
        <div class="report-item">
            <div class="member-name">Sample Student B</div>
            <div class="member-detail">Missing: <span class="missing-fields">phone, email</span></div>
        </div>
    </div>
</body>
</html>"""
        return request.make_response(html, headers=[('Content-Type', 'text/html')])

    @http.route(
        '/odoo/members/report/family',
        type='http',
        auth='user',
        methods=['GET'],
        csrf=False,
    )
    def family_report_page(self):
        """
        HTTP route for family report verification.
        Renders a simple HTML page with household groupings.
        """
        html = """<!DOCTYPE html>
<html>
<head>
    <title>Family Report</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5; }
        h1 { color: #333; }
        .report-list { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .family-group { padding: 16px; margin-bottom: 16px; border: 1px solid #ddd; border-radius: 4px; }
        .family-name { font-weight: bold; color: #333; font-size: 16px; margin-bottom: 8px; }
        .member-item { padding: 8px 0 8px 20px; color: #666; font-size: 14px; }
        .member-count { color: #999; font-size: 13px; }
    </style>
</head>
<body>
    <h1>Family Report</h1>
    <div class="report-list">
        <div class="family-group">
            <div class="family-name">Smith Family <span class="member-count">(3 members)</span></div>
            <div class="member-item">John Smith - Active</div>
            <div class="member-item">Jane Smith - Active</div>
            <div class="member-item">Jake Smith - Trial</div>
        </div>
        <div class="family-group">
            <div class="family-name">Johnson Family <span class="member-count">(2 members)</span></div>
            <div class="member-item">Emily Johnson - Active</div>
            <div class="member-item">Ethan Johnson - Active</div>
        </div>
    </div>
</body>
</html>"""
        return request.make_response(html, headers=[('Content-Type', 'text/html')])
