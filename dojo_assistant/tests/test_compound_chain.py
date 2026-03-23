# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestCompoundPhraseDetection(TransactionCase):
    """Tests for compound command phrase detection heuristic."""

    def setUp(self):
        super().setUp()
        self.svc = self.env["ai.assistant.service"]

    # ─── Should detect as compound ───────────────────────────────────────────

    def test_and_then_enroll(self):
        self.assertTrue(self.svc._is_compound_phrase("Enroll John and then create his subscription"))

    def test_and_text(self):
        self.assertTrue(self.svc._is_compound_phrase("Check in Mary and text her guardian"))

    def test_and_schedule(self):
        self.assertTrue(self.svc._is_compound_phrase("Promote John and schedule his belt test"))

    def test_then_send(self):
        self.assertTrue(self.svc._is_compound_phrase("Cancel the class then send a message"))

    # ─── Should NOT detect as compound ───────────────────────────────────────

    def test_single_enroll(self):
        self.assertFalse(self.svc._is_compound_phrase("Enroll John in BJJ Tuesday 6pm"))

    def test_comma_params_not_compound(self):
        """Comma-separated parameters in a single intent should not trigger compound."""
        self.assertFalse(self.svc._is_compound_phrase("Enroll John Smith, BJJ, Tuesday 6pm"))

    def test_lookup_only(self):
        self.assertFalse(self.svc._is_compound_phrase("Look up John Smith"))

    def test_and_without_verb(self):
        """'and' without a recognisable action verb should not trigger."""
        self.assertFalse(self.svc._is_compound_phrase("John and Mary attendance"))
