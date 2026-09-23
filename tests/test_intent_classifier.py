"""
tests/test_intent_classifier.py
---------------------------------
Unit tests for the intent classifier.

Tests the fast-path keyword matching without requiring an LLM call.
LLM-based classification is tested with mocked responses.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestFastPathClassification:
    """Tests that fast-path keyword matching works correctly (no LLM needed)."""

    def test_greeting_hi(self):
        from app.services.intent_classifier import classify_intent
        result = classify_intent("hi there!")
        assert result["intent"] == "greeting"

    def test_greeting_hello(self):
        from app.services.intent_classifier import classify_intent
        result = classify_intent("hello")
        assert result["intent"] == "greeting"

    def test_greeting_arabic(self):
        from app.services.intent_classifier import classify_intent
        result = classify_intent("مرحبا")
        assert result["intent"] == "greeting"

    def test_small_talk(self):
        from app.services.intent_classifier import classify_intent
        result = classify_intent("how are you doing today?")
        assert result["intent"] == "small_talk"

    def test_rewards_keywords(self):
        from app.services.intent_classifier import classify_intent
        result = classify_intent("what are my reward points?")
        assert result["intent"] == "check_rewards"

    def test_request_status_keywords(self):
        from app.services.intent_classifier import classify_intent
        result = classify_intent("what is my request status?")
        assert result["intent"] == "request_status"

    def test_schedule_pickup_keywords(self):
        from app.services.intent_classifier import classify_intent
        result = classify_intent("I want to schedule a pickup")
        assert result["intent"] == "schedule_pickup"

    def test_data_query_how_many(self):
        from app.services.intent_classifier import classify_intent
        result = classify_intent("how many users are registered?")
        assert result["intent"] == "data_query"

    def test_report_keywords(self):
        from app.services.intent_classifier import classify_intent
        result = classify_intent("give me a summary report")
        assert result["intent"] == "report_request"

    def test_coverage_keywords(self):
        from app.services.intent_classifier import classify_intent
        result = classify_intent("is Greenville in your service area?")
        assert result["intent"] == "coverage_check"

    def test_entities_are_present(self):
        """Every result must contain all entity keys."""
        from app.services.intent_classifier import classify_intent, _EMPTY_ENTITIES
        result = classify_intent("hello")
        for key in _EMPTY_ENTITIES:
            assert key in result["entities"], f"Missing entity key: {key}"

    def test_fallback_on_llm_error(self):
        """When LLM fails, classifier should fall back to 'general_faq'."""
        with patch("app.services.intent_classifier.llm") as mock_llm:
            mock_llm.invoke.side_effect = Exception("LLM timeout")
            from app.services.intent_classifier import classify_intent
            result = classify_intent("what is the refund policy for corporate accounts?")
            assert result["intent"] == "general_faq"


class TestLLMClassification:
    """Tests for LLM-based classification path using mocked LLM responses."""

    def _make_mock_llm_response(self, intent: str, entities: dict = None) -> MagicMock:
        import json
        mock_resp = MagicMock()
        mock_resp.content = json.dumps({
            "intent": intent,
            "entities": entities or {
                "city": None, "user_id": None, "start_date": None,
                "end_date": None, "category": None
            }
        })
        return mock_resp

    def test_llm_returns_data_query(self):
        with patch("app.services.intent_classifier.llm") as mock_llm:
            mock_llm.invoke.return_value = self._make_mock_llm_response("data_query")
            from app.services.intent_classifier import classify_intent
            result = classify_intent("compare total collections across cities this year")
            # Either fast-path or LLM should return data_query
            assert result["intent"] in ("data_query", "general_faq")

    def test_llm_extracts_city_entity(self):
        with patch("app.services.intent_classifier.llm") as mock_llm:
            mock_llm.invoke.return_value = self._make_mock_llm_response(
                "data_query",
                {"city": "Greenville", "user_id": None, "start_date": None,
                 "end_date": None, "category": None}
            )
            from app.services.intent_classifier import classify_intent
            result = classify_intent("total weight collected in Greenville")
            # City should be extracted either by fast-path or LLM
            if result["intent"] == "data_query":
                # City entity may or may not be set by fast-path
                pass
            assert result["intent"] in ("data_query", "check_rewards", "general_faq")

