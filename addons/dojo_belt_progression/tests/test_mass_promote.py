from odoo.tests import tagged, TransactionCase
from odoo.fields import Date
from datetime import datetime, timedelta


@tagged('post_install', '-at_install', 'dojo_belt_progression')
class TestMassPromote(TransactionCase):

    def setUp(self):
        super().setUp()

        # Get or create test belt ranks with unique sequences to avoid conflicts
        self.rank_white = self.env['dojo.belt.rank'].create({
            'name': 'Test White Belt',
            'sequence': 1001,
            'color': '#ffffff',
        })
        self.rank_yellow = self.env['dojo.belt.rank'].create({
            'name': 'Test Yellow Belt',
            'sequence': 1002,
            'color': '#ffff00',
        })
        self.rank_orange = self.env['dojo.belt.rank'].create({
            'name': 'Test Orange Belt',
            'sequence': 1003,
            'color': '#ffa500',
        })

        # Create test members without initial ranks
        self.member1 = self.env['dojo.member'].create({
            'name': 'John Smith Test',
            'membership_state': 'active',
        })
        self.member2 = self.env['dojo.member'].create({
            'name': 'Jane Doe Test',
            'membership_state': 'active',
        })
        self.member3 = self.env['dojo.member'].create({
            'name': 'Bob Johnson Test',
            'membership_state': 'active',
        })

    def test_mass_promote_creates_rank_records(self):
        """Test that mass promotion creates dojo.member.rank records."""
        # Initial state: members have no ranks
        self.assertFalse(self.member1.current_rank_id)
        self.assertFalse(self.member2.current_rank_id)

        members = self.member1 | self.member2

        # Promote both members to yellow belt
        for member in members:
            self.env['dojo.member.rank'].create({
                'member_id': member.id,
                'rank_id': self.rank_yellow.id,
                'date_awarded': Date.today(),
                'notes': f'Mass promotion to {self.rank_yellow.name}',
            })

        # Invalidate cache to ensure fresh read
        self.member1.invalidate_recordset()
        self.member2.invalidate_recordset()

        # Verify rank records were created
        self.assertEqual(self.member1.current_rank_id.id, self.rank_yellow.id)
        self.assertEqual(self.member2.current_rank_id.id, self.rank_yellow.id)

        # Check rank history
        self.assertEqual(len(self.member1.rank_history_ids), 1)
        self.assertEqual(len(self.member2.rank_history_ids), 1)

    def test_undo_promotion_deletes_records(self):
        """Test that undo deletes the specified rank records."""
        # Give member1 an initial rank
        initial_rank_record = self.env['dojo.member.rank'].create({
            'member_id': self.member1.id,
            'rank_id': self.rank_white.id,
            'date_awarded': Date.today() - timedelta(days=30),
        })

        self.member1.invalidate_recordset()
        self.assertEqual(self.member1.current_rank_id.id, self.rank_white.id)

        # Create a promotion record with a later date
        rank_record = self.env['dojo.member.rank'].create({
            'member_id': self.member1.id,
            'rank_id': self.rank_orange.id,
            'date_awarded': Date.today(),
            'notes': 'Test promotion',
        })

        # Invalidate cache and re-read
        self.member1.invalidate_recordset()

        # Verify current rank is orange
        self.assertEqual(self.member1.current_rank_id.id, self.rank_orange.id)

        # Undo by deleting the record
        rank_record.unlink()

        # Verify current rank reverted to white
        self.member1.invalidate_recordset()
        self.assertEqual(self.member1.current_rank_id.id, self.rank_white.id)

    def test_promotion_history_ordered_by_date(self):
        """Test that promotion history is ordered by date_awarded desc."""
        # Create multiple promotions with different dates
        self.env['dojo.member.rank'].create({
            'member_id': self.member1.id,
            'rank_id': self.rank_white.id,
            'date_awarded': '2025-01-01',
        })
        self.env['dojo.member.rank'].create({
            'member_id': self.member1.id,
            'rank_id': self.rank_yellow.id,
            'date_awarded': '2025-01-15',
        })
        self.env['dojo.member.rank'].create({
            'member_id': self.member1.id,
            'rank_id': self.rank_orange.id,
            'date_awarded': '2025-02-01',
        })

        # Get history ordered by date desc
        history = self.env['dojo.member.rank'].search([
            ('member_id', '=', self.member1.id)
        ], order='date_awarded desc')

        # Most recent should be first (compare IDs, not recordsets)
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0].rank_id.id, self.rank_orange.id)
        self.assertEqual(history[1].rank_id.id, self.rank_yellow.id)
        self.assertEqual(history[2].rank_id.id, self.rank_white.id)

    def test_multiple_members_promoted_to_same_rank(self):
        """Test promoting multiple members to the same rank simultaneously."""
        # Start with no ranks
        self.assertFalse(self.member1.current_rank_id)
        self.assertFalse(self.member2.current_rank_id)
        self.assertFalse(self.member3.current_rank_id)

        members = self.member1 | self.member2 | self.member3

        # Promote all to orange belt
        for member in members:
            self.env['dojo.member.rank'].create({
                'member_id': member.id,
                'rank_id': self.rank_orange.id,
                'date_awarded': Date.today(),
            })

        # Invalidate cache
        members.invalidate_recordset()

        # Verify all are now orange belt
        self.assertEqual(self.member1.current_rank_id.id, self.rank_orange.id)
        self.assertEqual(self.member2.current_rank_id.id, self.rank_orange.id)
        self.assertEqual(self.member3.current_rank_id.id, self.rank_orange.id)

    def test_promotion_notes_stored(self):
        """Test that promotion notes are stored correctly."""
        test_note = 'Excellent performance in belt test'

        rank_record = self.env['dojo.member.rank'].create({
            'member_id': self.member1.id,
            'rank_id': self.rank_yellow.id,
            'date_awarded': Date.today(),
            'notes': test_note,
        })

        self.assertEqual(rank_record.notes, test_note)
