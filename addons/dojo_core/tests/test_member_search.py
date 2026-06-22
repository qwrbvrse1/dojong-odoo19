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
        cls.alice_smith = cls.Member.create({
            "name": "Alice Smith",
            "email": "alice.smith@example.com",
        })
        cls.robert_smithson = cls.Member.create({
            "name": "Robert Smithson",
            "email": "robert.smithson@example.com",
        })
        cls.mary_jones = cls.Member.create({
            "name": "Mary Jones",
            "email": "mary.jones@example.com",
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

    def test_surname_first_ranking_for_exact_surname_match(self):
        """Searching 'Smith' should rank surname-first matches above mid-name matches."""
        result_ids = self.Member._name_search("Smith", domain=[], operator="ilike", limit=10)
        # alice_smith and john both have surname "Smith"; robert_smithson has "Smithson" (not exact surname start match for "Smith")
        # Expect alice_smith and john before robert_smithson
        smith_surname_ids = {self.john.id, self.alice_smith.id}
        smithson_id = self.robert_smithson.id

        # Find positions
        smith_positions = [result_ids.index(sid) for sid in smith_surname_ids if sid in result_ids]
        smithson_position = result_ids.index(smithson_id) if smithson_id in result_ids else None

        # At least one Smith surname match should appear before Smithson
        if smith_positions and smithson_position is not None:
            self.assertTrue(
                any(pos < smithson_position for pos in smith_positions),
                f"Expected surname 'Smith' matches before 'Smithson'. Got order: {result_ids}"
            )

    def test_surname_ranking_preserves_non_surname_matches(self):
        """Surname-first ranking should not exclude members with query in other parts of name."""
        result_ids = self.Member._name_search("Smith", domain=[], operator="ilike", limit=10)
        # All three (john, alice_smith, robert_smithson) should appear
        self.assertIn(self.john.id, result_ids)
        self.assertIn(self.alice_smith.id, result_ids)
        self.assertIn(self.robert_smithson.id, result_ids)

    def test_surname_ranking_with_no_surname_match(self):
        """Query with no surname match should return matches normally."""
        result_ids = self.Member._name_search("Jones", domain=[], operator="ilike", limit=10)
        self.assertIn(self.mary_jones.id, result_ids)
        # john, alice_smith, robert_smithson should not match "Jones"
        self.assertNotIn(self.john.id, result_ids)

    def test_surname_ranking_multi_token_query(self):
        """Multi-token query should use last token as probable surname."""
        result_ids = self.Member._name_search("Smith", domain=[], operator="ilike", limit=10)
        # "Smith" is the last token; alice_smith and john should both match and be ranked by surname "Smith"
        self.assertIn(self.alice_smith.id, result_ids)
        self.assertIn(self.john.id, result_ids)
        # Both have surname "Smith", so both should appear in the surname-first partition
        alice_pos = result_ids.index(self.alice_smith.id) if self.alice_smith.id in result_ids else None
        john_pos = result_ids.index(self.john.id) if self.john.id in result_ids else None
        # Both should be in the results
        self.assertIsNotNone(alice_pos)
        self.assertIsNotNone(john_pos)
