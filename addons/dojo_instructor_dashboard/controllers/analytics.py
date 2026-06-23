import logging
from datetime import date, timedelta

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class InstructorAnalyticsController(http.Controller):

    def _compute_analytics_data(self, env, days=30):
        """
        Computes attendance analytics data.

        Args:
            env: Odoo environment
            days: Number of days to look back (30 or 90)

        Returns:
            dict: Analytics data with busiest sessions, top members, and inactive members
        """
        Member = env['dojo.member']
        AttendanceLog = env['dojo.attendance.log']
        ClassSession = env['dojo.class.session']

        today = date.today()
        start_date = today - timedelta(days=days)

        # Top 10 sessions by check-in count (present + late)
        domain_log = [
            ('checkin_datetime', '>=', start_date.strftime('%Y-%m-%d 00:00:00')),
            ('status', 'in', ['present', 'late']),
        ]

        # Group attendance logs by session
        logs = AttendanceLog.search(domain_log)
        session_counts = {}
        for log in logs:
            session_id = log.session_id.id
            if session_id not in session_counts:
                session_counts[session_id] = 0
            session_counts[session_id] += 1

        # Get top 10 sessions
        top_sessions = sorted(session_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        busiest_sessions = []
        for session_id, count in top_sessions:
            session = ClassSession.browse(session_id)
            busiest_sessions.append({
                'session_id': session.id,
                'session_name': session.name or session.display_name,
                'checkin_count': count,
                'start_datetime': session.start_datetime.strftime('%Y-%m-%d %H:%M:%S') if session.start_datetime else '',
            })

        # Top 10 members by check-in count
        member_counts = {}
        for log in logs:
            member_id = log.member_id.id
            if member_id not in member_counts:
                member_counts[member_id] = 0
            member_counts[member_id] += 1

        top_members = sorted(member_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        top_attending_members = []
        for member_id, count in top_members:
            member = Member.browse(member_id)
            belt_name = member.current_rank_id.name if member.current_rank_id else "Unranked"
            top_attending_members.append({
                'member_id': member.id,
                'member_name': member.name,
                'belt': belt_name,
                'checkin_count': count,
            })

        # Inactive members (active members with zero attendance in the period)
        active_members = Member.search([('membership_state', '=', 'active')])
        inactive_members = []

        for member in active_members:
            recent_logs = AttendanceLog.search([
                ('member_id', '=', member.id),
                ('checkin_datetime', '>=', start_date.strftime('%Y-%m-%d 00:00:00')),
                ('status', 'in', ['present', 'late']),
            ], limit=1)

            if not recent_logs:
                # Find last attendance ever
                last_log = AttendanceLog.search([
                    ('member_id', '=', member.id),
                    ('status', 'in', ['present', 'late']),
                ], order='checkin_datetime desc', limit=1)

                last_seen = last_log.checkin_datetime.strftime('%Y-%m-%d') if last_log else 'Never'
                belt_name = member.current_rank_id.name if member.current_rank_id else "Unranked"

                inactive_members.append({
                    'member_id': member.id,
                    'member_name': member.name,
                    'belt': belt_name,
                    'last_seen': last_seen,
                })

        return {
            'busiest_sessions': busiest_sessions,
            'top_attending_members': top_attending_members,
            'inactive_members': inactive_members,
            'period_days': days,
        }

    @http.route(
        '/instructor_dashboard/analytics',
        type='json',
        auth='user',
        methods=['GET', 'POST'],
    )
    def get_analytics_data(self, days=30):
        """
        Returns attendance analytics data.

        Query params:
            days: Number of days to look back (30 or 90), default 30

        Returns:
            dict: {
                "busiest_sessions": [{"session_id": int, "session_name": str, "checkin_count": int, "start_datetime": str}, ...],
                "top_attending_members": [{"member_id": int, "member_name": str, "belt": str, "checkin_count": int}, ...],
                "inactive_members": [{"member_id": int, "member_name": str, "belt": str, "last_seen": str}, ...],
                "period_days": int
            }
        """
        days = int(days) if days in [30, 90, '30', '90'] else 30
        return self._compute_analytics_data(request.env, days)
