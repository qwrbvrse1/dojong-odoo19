from odoo import http, fields, _
from odoo.http import request
from odoo.exceptions import AccessError
from datetime import timedelta
import json


class BeltPromotionController(http.Controller):
    """Controller for mass belt promotion operations."""

    def _check_instructor_access(self):
        """Verify the current user is an instructor or admin."""
        if not request.env.user.has_group('dojo_core.group_dojo_instructor') and \
           not request.env.user.has_group('dojo_core.group_dojo_admin'):
            raise AccessError(_('Only instructors and administrators may access belt promotion features.'))

    @http.route('/belt_progression/data', type='jsonrpc', auth='user')
    def get_promotion_data(self):
        """Return members and belt ranks for mass promotion UI."""
        self._check_instructor_access()

        Member = request.env['dojo.member']
        BeltRank = request.env['dojo.belt.rank']

        # Get all active members with their current rank
        members = Member.search([('active', '=', True)])
        member_data = []
        for member in members:
            current_rank = member.current_rank_id
            member_data.append({
                'id': member.id,
                'name': member.name,
                'current_rank_id': current_rank.id if current_rank else False,
                'current_rank_name': current_rank.name if current_rank else 'No Rank',
                'current_rank_color': current_rank.color if current_rank else '#cccccc',
            })

        # Get all belt ranks ordered by sequence
        ranks = BeltRank.search([('active', '=', True)], order='sequence ASC')
        rank_data = [{
            'id': rank.id,
            'name': rank.name,
            'sequence': rank.sequence,
            'color': rank.color,
        } for rank in ranks]

        return {
            'members': member_data,
            'ranks': rank_data,
        }

    @http.route('/belt_progression/promote', type='jsonrpc', auth='user')
    def promote_members(self, member_ids, target_rank_id):
        """
        Promote multiple members to a target rank.
        Returns the created rank records for undo support.
        """
        self._check_instructor_access()

        Member = request.env['dojo.member']
        BeltRank = request.env['dojo.belt.rank']
        MemberRank = request.env['dojo.member.rank']

        if not member_ids or not target_rank_id:
            return {'error': 'Missing member_ids or target_rank_id'}

        target_rank = BeltRank.browse(target_rank_id)
        if not target_rank.exists():
            return {'error': 'Invalid target rank'}

        created_records = []
        for member_id in member_ids:
            member = Member.browse(member_id)
            if not member.exists():
                continue

            # Create new rank record
            rank_record = MemberRank.create({
                'member_id': member.id,
                'rank_id': target_rank.id,
                'date_awarded': http.request.env.context.get('date_awarded', False) or fields.Date.today(),
                'awarded_by': False,  # Could be populated with current instructor
                'notes': f'Mass promotion to {target_rank.name}',
            })
            created_records.append({
                'id': rank_record.id,
                'member_id': member.id,
                'rank_id': target_rank.id,
            })

        return {
            'success': True,
            'promoted_count': len(created_records),
            'records': created_records,
        }

    @http.route('/belt_progression/undo', type='jsonrpc', auth='user')
    def undo_promotion(self, record_ids):
        """
        Undo a promotion by deleting the specified rank records.
        Used for in-session undo only. Restricted to records created by the current user
        within the last 10 minutes to prevent unauthorized deletion.
        """
        self._check_instructor_access()

        MemberRank = request.env['dojo.member.rank']

        if not record_ids:
            return {'error': 'No record_ids provided'}

        # Security: Only allow undo of records created by this user within the last 10 minutes
        cutoff_time = fields.Datetime.now() - timedelta(minutes=10)
        records = MemberRank.search([
            ('id', 'in', record_ids),
            ('create_uid', '=', request.env.uid),
            ('create_date', '>=', cutoff_time),
        ])

        if not records:
            return {'error': 'No eligible records found. Undo is only allowed for promotions you created within the last 10 minutes.'}

        deleted_count = len(records)
        records.unlink()

        return {
            'success': True,
            'deleted_count': deleted_count,
        }
