from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestKioskMemberSearch(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.member = cls.env["dojo.member"].with_context(
            mail_create_nolog=True,
            tracking_disable=True,
        ).create({
            "name": "John Smith",
            "email": "john.smith@example.com",
            "phone": "(555) 123-4567",
            "member_number": "DJ-00992",
        })
        cls.KioskService = cls.env["dojo.kiosk.service"]

    def _result_ids(self, query):
        return {
            result.get("member_id")
            for result in self.KioskService.search_members(query)
            if result.get("member_id")
        }

    def test_kiosk_search_uses_shared_member_lookup(self):
        for query in ("Smith", "Smi", "John Smith", "Smith J"):
            with self.subTest(query=query):
                self.assertIn(self.member.id, self._result_ids(query))

    def test_kiosk_search_preserves_email_and_phone_lookup(self):
        self.assertIn(self.member.id, self._result_ids("john.smith@example.com"))
        self.assertIn(self.member.id, self._result_ids("555123"))
        self.assertIn(self.member.id, self._result_ids("DJ00992"))
