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


class TestCompoundParsing(TransactionCase):
    """Tests for compound intent detection in _parse_intent_response."""

    def setUp(self):
        super().setUp()
        self.proc = self.env["ai.processor"]

    def test_single_intent_unchanged(self):
        """Single-intent JSON response still works normally."""
        raw = '{"intent_type": "member_lookup", "parameters": {"member_name": "John"}, "confidence": 0.9, "resolved_entities": {}, "reasoning": "lookup"}'
        result = self.proc._parse_intent_response(raw)
        self.assertEqual(result["intent_type"], "member_lookup")
        self.assertNotIn("intents", result)

    def test_compound_intent_detected(self):
        """Response with 'intents' key is returned as-is (compound)."""
        raw = '''{
            "intents": [
                {"intent_type": "member_enroll", "parameters": {"member_name": "John"}, "confidence": 0.9, "resolved_entities": {}},
                {"intent_type": "contact_parent", "parameters": {"member_name": "John"}, "confidence": 0.85, "resolved_entities": {}}
            ],
            "reasoning": "two actions"
        }'''
        result = self.proc._parse_intent_response(raw)
        self.assertIn("intents", result)
        self.assertEqual(len(result["intents"]), 2)
        self.assertEqual(result["intents"][0]["intent_type"], "member_enroll")

    def test_compound_missing_fields_preserved(self):
        """Compound response is not modified — validation is in handle_compound_command()."""
        raw = '{"intents": [{"intent_type": "member_enroll", "confidence": 0.9}], "reasoning": ""}'
        result = self.proc._parse_intent_response(raw)
        self.assertIn("intents", result)
        self.assertNotIn("parameters", result["intents"][0])


class TestHandleCompoundCommand(TransactionCase):
    """Tests for compound command validation and confirmation building."""

    def setUp(self):
        super().setUp()
        self.svc = self.env["ai.assistant.service"]

    def _make_intent(self, intent_type, confidence=0.9, params=None):
        return {
            "intent_type": intent_type,
            "parameters": params or {},
            "confidence": confidence,
            "resolved_entities": {},
        }

    def test_empty_intents_rejected(self):
        """Empty intents list returns an error."""
        result = self.svc.handle_compound_command({"intents": [], "reasoning": ""}, role="instructor")
        self.assertFalse(result["success"])
        self.assertIn("no intents", result["error"].lower())

    def test_max_chain_exceeded(self):
        """More than 5 intents returns an error."""
        intents = [self._make_intent("member_lookup") for _ in range(6)]
        result = self.svc.handle_compound_command(
            {"intents": intents, "reasoning": "test"}, role="instructor"
        )
        self.assertFalse(result["success"])
        self.assertIn("maximum", result["error"].lower())

    def test_low_confidence_rejected(self):
        """Any intent with confidence < 0.7 rejects the whole chain."""
        intents = [
            self._make_intent("member_lookup", confidence=0.9),
            self._make_intent("member_enroll", confidence=0.5),
        ]
        result = self.svc.handle_compound_command(
            {"intents": intents, "reasoning": ""}, role="instructor"
        )
        self.assertFalse(result["success"])
        self.assertIn("confidence", result["error"].lower())

    def test_unknown_intent_type_rejected(self):
        """An unrecognised intent_type rejects the chain."""
        intents = [self._make_intent("made_up_intent", confidence=0.9)]
        result = self.svc.handle_compound_command(
            {"intents": intents, "reasoning": ""}, role="instructor"
        )
        self.assertFalse(result["success"])
        self.assertIn("unrecognised", result["error"].lower())

    def test_valid_chain_returns_pending_confirmation(self):
        """A valid 2-step chain returns state pending_confirmation."""
        intents = [
            self._make_intent("member_lookup", confidence=0.9, params={"member_name": "Test"}),
            self._make_intent("attendance_history", confidence=0.85, params={"member_name": "Test"}),
        ]
        result = self.svc.handle_compound_command(
            {"intents": intents, "reasoning": ""}, role="instructor"
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["state"], "pending_confirmation")
        self.assertIn("session_key", result)
        self.assertIn("1.", result["confirmation_prompt"])
        self.assertIn("2.", result["confirmation_prompt"])

    def test_compound_chain_log_record_created(self):
        """A compound_chain log record is written to dojo.ai.action.log."""
        intents = [
            self._make_intent("member_lookup", confidence=0.9, params={"member_name": "Test"}),
        ]
        result = self.svc.handle_compound_command(
            {"intents": intents, "reasoning": ""}, role="instructor"
        )
        log = self.env["dojo.ai.action.log"].search(
            [("session_key", "=", result.get("session_key"))]
        )
        self.assertEqual(len(log), 1)
        self.assertEqual(log.intent_type, "compound_chain")
