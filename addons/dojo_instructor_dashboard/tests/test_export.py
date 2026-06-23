import csv
import io
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDojoExport(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create test data: members, attendance, ranks, belt tests
        cls.belt_rank = cls.env["dojo.belt.rank"].create({
            "name": "White Belt",
            "sequence": 1,
            "color": "#FFFFFF",
        })

        cls.member_1 = cls.env["dojo.member"].create({
            "name": "John Smith",
            "first_name": "John",
            "last_name": "Smith",
            "email": "john@example.com",
            "phone": "555-1234",
            "date_of_birth": "2010-05-15",
            "gender": "male",
            "membership_state": "active",
            "blood_type": "O+",
            "allergies": "None",
        })

        cls.member_2 = cls.env["dojo.member"].create({
            "name": "Jane Doe",
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane@example.com",
            "phone": "555-5678",
            "date_of_birth": "2012-08-20",
            "gender": "female",
            "membership_state": "trial",
        })

        # Create emergency contact
        cls.env["dojo.emergency.contact"].create({
            "member_id": cls.member_1.id,
            "name": "Parent Smith",
            "relationship": "Parent",
            "phone": "555-9999",
        })

        # Create class session
        cls.class_template = cls.env["dojo.class.template"].create({
            "name": "Test Class",
        })

        cls.session = cls.env["dojo.class.session"].create({
            "template_id": cls.class_template.id,
            "start_datetime": "2026-06-23 10:00:00",
            "end_datetime": "2026-06-23 11:00:00",
        })

        # Create attendance logs
        cls.attendance_1 = cls.env["dojo.attendance.log"].create({
            "session_id": cls.session.id,
            "member_id": cls.member_1.id,
            "status": "present",
            "checkin_datetime": "2026-06-23 10:05:00",
            "checkout_datetime": "2026-06-23 11:00:00",
        })

        cls.attendance_2 = cls.env["dojo.attendance.log"].create({
            "session_id": cls.session.id,
            "member_id": cls.member_2.id,
            "status": "late",
            "checkin_datetime": "2026-06-23 10:20:00",
        })

        # Create rank history
        cls.rank_1 = cls.env["dojo.member.rank"].create({
            "member_id": cls.member_1.id,
            "rank_id": cls.belt_rank.id,
            "date_awarded": "2026-05-01",
            "stripe_count": 0,
        })

        # Create belt test
        cls.belt_test = cls.env["dojo.belt.test"].create({
            "name": "Test Belt Exam",
            "test_date": "2026-07-01",
            "location": "Main Dojo",
            "state": "scheduled",
        })

    def test_export_students(self):
        """Test student export includes all expected fields."""
        wizard = self.env["dojo.export.wizard"].create({
            "export_type": "students",
        })

        csv_data = wizard._export_students()
        self.assertTrue(csv_data, "CSV data should not be empty")

        # Parse CSV
        reader = csv.DictReader(io.StringIO(csv_data))
        rows = list(reader)

        # Should have at least 2 members
        self.assertGreaterEqual(len(rows), 2, "Should export at least 2 members")

        # Check first member data
        john_row = next((r for r in rows if r["Name"] == "John Smith"), None)
        self.assertIsNotNone(john_row, "John Smith should be in export")
        self.assertEqual(john_row["First Name"], "John")
        self.assertEqual(john_row["Last Name"], "Smith")
        self.assertEqual(john_row["Email"], "john@example.com")
        self.assertEqual(john_row["Gender"], "Male")
        self.assertEqual(john_row["Blood Type"], "O+")
        self.assertIn("Parent Smith", john_row["Emergency Contact"])

    def test_export_attendance(self):
        """Test attendance log export."""
        wizard = self.env["dojo.export.wizard"].create({
            "export_type": "attendance",
        })

        csv_data = wizard._export_attendance()
        self.assertTrue(csv_data, "CSV data should not be empty")

        # Parse CSV
        reader = csv.DictReader(io.StringIO(csv_data))
        rows = list(reader)

        # Should have at least 2 attendance logs
        self.assertGreaterEqual(len(rows), 2, "Should export at least 2 attendance logs")

        # Check first attendance
        john_attendance = next((r for r in rows if r["Member Name"] == "John Smith"), None)
        self.assertIsNotNone(john_attendance, "John Smith attendance should be in export")
        self.assertEqual(john_attendance["Status"], "Present")

    def test_export_promotion_history(self):
        """Test promotion history export."""
        wizard = self.env["dojo.export.wizard"].create({
            "export_type": "promotion_history",
        })

        csv_data = wizard._export_promotion_history()
        self.assertTrue(csv_data, "CSV data should not be empty")

        # Parse CSV
        reader = csv.DictReader(io.StringIO(csv_data))
        rows = list(reader)

        # Should have at least 1 promotion
        self.assertGreaterEqual(len(rows), 1, "Should export at least 1 promotion")

        # Check promotion data
        john_rank = next((r for r in rows if r["Member Name"] == "John Smith"), None)
        self.assertIsNotNone(john_rank, "John Smith promotion should be in export")
        self.assertEqual(john_rank["Belt Rank"], "White Belt")
        self.assertEqual(john_rank["Stripes"], "0")

    def test_export_belt_test_rosters(self):
        """Test belt test roster export."""
        wizard = self.env["dojo.export.wizard"].create({
            "export_type": "belt_test_rosters",
        })

        csv_data = wizard._export_belt_test_rosters()
        self.assertTrue(csv_data, "CSV data should not be empty")

        # Parse CSV - should have header even if no registrations
        reader = csv.DictReader(io.StringIO(csv_data))
        rows = list(reader)

        # Belt test exists but may have no registrations yet
        # Just verify CSV structure is correct
        self.assertIsNotNone(reader.fieldnames, "CSV should have headers")
        self.assertIn("Test Name", reader.fieldnames)
        self.assertIn("Member Name", reader.fieldnames)

    def test_export_controller(self):
        """Test the export controller logic via wizard methods."""
        # Rather than mocking the HTTP layer, test the wizard methods directly
        # since the controller delegates to them
        wizard = self.env["dojo.export.wizard"].create({
            "export_type": "students",
        })

        # Test that wizard can generate CSV for each export type
        csv_students = wizard._export_students()
        self.assertTrue(csv_students, "Students export should return CSV data")
        self.assertIn("Member Number", csv_students, "Should have header row")
        self.assertIn("John Smith", csv_students, "Should contain member data")

        wizard.write({"export_type": "attendance"})
        csv_attendance = wizard._export_attendance()
        self.assertTrue(csv_attendance, "Attendance export should return CSV data")
        self.assertIn("Check-in Time", csv_attendance, "Should have header row")

        wizard.write({"export_type": "promotion_history"})
        csv_promotions = wizard._export_promotion_history()
        self.assertTrue(csv_promotions, "Promotion export should return CSV data")
        self.assertIn("Belt Rank", csv_promotions, "Should have header row")

        wizard.write({"export_type": "belt_test_rosters"})
        csv_tests = wizard._export_belt_test_rosters()
        self.assertTrue(csv_tests, "Belt test export should return CSV data")
        self.assertIn("Test Name", csv_tests, "Should have header row")
