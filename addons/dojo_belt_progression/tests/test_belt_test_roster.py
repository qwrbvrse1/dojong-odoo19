from odoo.tests import tagged, TransactionCase


@tagged("post_install", "-at_install", "dojo_belt_progression")
class TestBeltTestRoster(TransactionCase):
    def setUp(self):
        super().setUp()

        # Create test program
        self.program = self.env["dojo.program"].create({
            "name": "Test Taekwondo",
            "code": "TTK",
        })

        # Create test ranks
        self.rank_white = self.env["dojo.belt.rank"].create({
            "name": "White Belt",
            "sequence": 10,
            "color": "#ffffff",
        })
        self.rank_yellow = self.env["dojo.belt.rank"].create({
            "name": "Yellow Belt",
            "sequence": 20,
            "color": "#ffff00",
        })
        self.rank_green = self.env["dojo.belt.rank"].create({
            "name": "Green Belt",
            "sequence": 30,
            "color": "#00ff00",
        })

        # Create test class template
        self.template = self.env["dojo.class.template"].create({
            "name": "Kids Taekwondo",
            "program_id": self.program.id,
            "level": "beginner",
        })

        # Create test members
        self.member1 = self.env["dojo.member"].create({
            "name": "Alice Smith",
            "membership_state": "active",
        })
        self.member2 = self.env["dojo.member"].create({
            "name": "Bob Johnson",
            "membership_state": "active",
        })
        self.member3 = self.env["dojo.member"].create({
            "name": "Charlie Brown",
            "membership_state": "active",
        })

        # Assign current ranks
        self.env["dojo.member.rank"].create({
            "member_id": self.member1.id,
            "rank_id": self.rank_white.id,
            "program_id": self.program.id,
        })
        self.env["dojo.member.rank"].create({
            "member_id": self.member2.id,
            "rank_id": self.rank_yellow.id,
            "program_id": self.program.id,
        })

    def test_save_roster_creates_belt_test(self):
        """Test saving a roster creates a belt test with registrations."""
        BeltTest = self.env["dojo.belt.test"]

        test_data = {
            "name": "Spring Belt Test 2026",
            "test_date": "2026-06-30",
            "program_id": self.program.id,
            "state": "scheduled",
        }

        belt_test = BeltTest.create(test_data)

        self.assertEqual(belt_test.name, "Spring Belt Test 2026")
        self.assertEqual(belt_test.state, "scheduled")
        self.assertEqual(str(belt_test.test_date), "2026-06-30")

        # Create registrations
        Registration = self.env["dojo.belt.test.registration"]
        reg1 = Registration.create({
            "test_id": belt_test.id,
            "member_id": self.member1.id,
            "target_rank_id": self.rank_yellow.id,
        })
        reg2 = Registration.create({
            "test_id": belt_test.id,
            "member_id": self.member2.id,
            "target_rank_id": self.rank_green.id,
        })

        self.assertEqual(len(belt_test.registration_ids), 2)
        self.assertIn(reg1, belt_test.registration_ids)
        self.assertIn(reg2, belt_test.registration_ids)

    def test_roster_filter_by_rank(self):
        """Test filtering members by current rank."""
        # Members with white belt
        white_members = self.env["dojo.member"].search([
            ("active", "=", True),
        ]).filtered(lambda m: m.current_rank_id == self.rank_white)

        self.assertIn(self.member1, white_members)
        self.assertNotIn(self.member2, white_members)
        self.assertNotIn(self.member3, white_members)

        # Members with yellow belt
        yellow_members = self.env["dojo.member"].search([
            ("active", "=", True),
        ]).filtered(lambda m: m.current_rank_id == self.rank_yellow)

        self.assertIn(self.member2, yellow_members)
        self.assertNotIn(self.member1, yellow_members)

    def test_belt_test_state_workflow(self):
        """Test belt test state transitions."""
        belt_test = self.env["dojo.belt.test"].create({
            "name": "Test Workflow",
            "test_date": "2026-07-01",
            "state": "scheduled",
        })

        self.assertEqual(belt_test.state, "scheduled")

        belt_test.action_start()
        self.assertEqual(belt_test.state, "in_progress")

        belt_test.action_complete()
        self.assertEqual(belt_test.state, "completed")

    def test_next_rank_calculation(self):
        """Test calculating the next rank in sequence."""
        Rank = self.env["dojo.belt.rank"]

        # For member1 with white belt, next should be yellow
        current_rank = self.member1.current_rank_id
        next_rank = Rank.search([
            ('sequence', '>', current_rank.sequence),
            ('active', '=', True)
        ], order='sequence', limit=1)

        self.assertEqual(next_rank, self.rank_yellow)

        # For member2 with yellow belt, next should be green
        current_rank = self.member2.current_rank_id
        next_rank = Rank.search([
            ('sequence', '>', current_rank.sequence),
            ('active', '=', True)
        ], order='sequence', limit=1)

        self.assertEqual(next_rank, self.rank_green)

        # For member3 with no rank, first rank should be white
        self.assertFalse(self.member3.current_rank_id)
        first_rank = Rank.search([('active', '=', True)], order='sequence', limit=1)
        self.assertEqual(first_rank, self.rank_white)
