from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDojoMemberSearch(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Member = cls.env["dojo.member"].with_context(
            mail_create_nolog=True,
            tracking_disable=True,
        )
        cls.john = cls.Member.create({
            "name": "John Smith",
            "email": "john.smith@example.com",
            "phone": "(555) 123-4567",
            "member_number": "DJ-00991",
        })
        cls.legacy = cls.Member.create({
            "name": "Lee, Harper",
            "email": "harper.lee@example.com",
        })

    def _lookup(self, query):
        return self.Member.search_for_lookup(query, limit=20)

    def test_lookup_matches_surname_and_full_name_forms(self):
        for query in ("Smith", "Smi", "John Smith", "Smith J"):
            with self.subTest(query=query):
                self.assertIn(self.john, self._lookup(query))

    def test_lookup_preserves_email_and_phone_search(self):
        self.assertIn(self.john, self._lookup("john.smith@example.com"))
        self.assertIn(self.john, self._lookup("555123"))
        self.assertIn(self.john, self._lookup("DJ00991"))

    def test_legacy_name_is_split_for_reversed_search(self):
        self.assertEqual(self.legacy.first_name, "Harper")
        self.assertEqual(self.legacy.last_name, "Lee")
        self.assertIn(self.legacy, self._lookup("Lee H"))

    def test_display_name_and_name_search_use_member_lookup(self):
        self.assertIn(
            self.john,
            self.Member.search([("display_name", "ilike", "Smith J")]),
        )
        result_ids = [record_id for record_id, _name in self.Member.name_search("Smith J")]
        self.assertIn(self.john.id, result_ids)
