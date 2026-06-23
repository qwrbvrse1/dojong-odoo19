import logging
from datetime import date, timedelta

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class InstructorDashboardController(http.Controller):

    def _compute_dashboard_data(self, env):
        """
        Computes dashboard data. Separated for testability.

        Args:
            env: Odoo environment

        Returns:
            dict: Dashboard data
        """
        Member = env['dojo.member']
        AttendanceLog = env['dojo.attendance.log']
        BeltRank = env['dojo.belt.rank']

        today = date.today()
        seven_days = today + timedelta(days=7)
        thirty_days = today + timedelta(days=30)

        # Stat 1: Active students count
        active_students = Member.search_count([('membership_state', '=', 'active')])

        # Stat 2: Today's check-ins (present + late)
        todays_checkins = AttendanceLog.search_count([
            ('checkin_datetime', '>=', today.strftime('%Y-%m-%d 00:00:00')),
            ('checkin_datetime', '<=', today.strftime('%Y-%m-%d 23:59:59')),
            ('status', 'in', ['present', 'late']),
        ])

        # Stat 3 & Birthday list: Upcoming birthdays (year-agnostic)
        all_active = Member.search([('membership_state', '=', 'active'), ('date_of_birth', '!=', False)])
        birthday_records = []
        for member in all_active:
            dob = member.date_of_birth
            # Calculate this year's birthday
            this_year_birthday = dob.replace(year=today.year)
            # If already passed, use next year
            if this_year_birthday < today:
                this_year_birthday = dob.replace(year=today.year + 1)

            days_until = (this_year_birthday - today).days

            if 0 <= days_until <= 7:
                belt_name = member.current_rank_id.name if member.current_rank_id else "Unranked"
                birthday_records.append({
                    'id': member.id,
                    'name': member.name,
                    'belt': belt_name,
                    'dob': dob.strftime('%Y-%m-%d'),
                    'days_until': days_until,
                })

        birthday_records.sort(key=lambda x: x['days_until'])
        upcoming_birthdays = len(birthday_records)

        # Stat 4 & Expiring list: Expiring memberships
        expiring_members = Member.search([
            ('membership_state', '=', 'active'),
            ('expdate', '!=', False),
            ('expdate', '<=', thirty_days),
        ], order='expdate asc')

        expiring_list = []
        for member in expiring_members:
            belt_name = member.current_rank_id.name if member.current_rank_id else "Unranked"
            expiring_list.append({
                'id': member.id,
                'name': member.name,
                'belt': belt_name,
                'expdate': member.expdate.strftime('%Y-%m-%d'),
            })

        expiring_memberships = len(expiring_list)

        # Belt distribution
        belt_distribution = []
        all_ranks = BeltRank.search([], order='sequence asc')

        for rank in all_ranks:
            count = Member.search_count([
                ('membership_state', '=', 'active'),
                ('current_rank_id', '=', rank.id),
            ])
            if count > 0:
                belt_distribution.append({
                    'rank': rank.name,
                    'color': rank.color or '#cccccc',
                    'count': count,
                })

        # Add unranked members
        unranked_count = Member.search_count([
            ('membership_state', '=', 'active'),
            ('current_rank_id', '=', False),
        ])
        if unranked_count > 0:
            belt_distribution.append({
                'rank': 'Unranked',
                'color': '#666666',
                'count': unranked_count,
            })

        return {
            'active_students': active_students,
            'todays_checkins': todays_checkins,
            'upcoming_birthdays': upcoming_birthdays,
            'expiring_memberships': expiring_memberships,
            'belt_distribution': belt_distribution,
            'birthday_list': birthday_records,
            'expiring_list': expiring_list,
        }

    @http.route(
        '/instructor_dashboard/data',
        type='jsonrpc',
        auth='user',
        methods=['POST'],
    )
    def get_dashboard_data(self):
        """
        Returns dashboard data for the instructor dashboard OWL component.

        Data structure:
        {
            "active_students": int,
            "todays_checkins": int,
            "upcoming_birthdays": int,
            "expiring_memberships": int,
            "belt_distribution": [{"rank": str, "color": str, "count": int}, ...],
            "birthday_list": [{"id": int, "name": str, "belt": str, "dob": str, "days_until": int}, ...],
            "expiring_list": [{"id": int, "name": str, "belt": str, "expdate": str}, ...]
        }
        """
        return self._compute_dashboard_data(request.env)
