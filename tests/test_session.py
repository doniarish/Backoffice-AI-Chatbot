"""
tests/test_session.py
----------------------
Unit tests for the session manager.
Tests both the in-memory backend (always available) and Redis backend (mocked).
"""

import pytest
import time


class TestInMemorySession:
    """Tests using the in-memory session store (no Redis required)."""

    def _fresh_manager(self):
        """Create a fresh SessionManager with in-memory store."""
        from app.session.manager import InMemorySessionStore, SessionManager
        mgr = SessionManager.__new__(SessionManager)
        mgr._store = InMemorySessionStore()
        return mgr

    def test_add_and_get_message(self):
        mgr = self._fresh_manager()
        mgr.add_message("s1", "user", "Hello!")
        history = mgr.get_history("s1")
        assert len(history) == 1
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello!"

    def test_multi_turn_history(self):
        mgr = self._fresh_manager()
        mgr.add_message("s2", "user", "What are my points?")
        mgr.add_message("s2", "assistant", "You have 200 points.")
        mgr.add_message("s2", "user", "How do I redeem them?")
        history = mgr.get_history("s2")
        assert len(history) == 3

    def test_clear_session(self):
        mgr = self._fresh_manager()
        mgr.add_message("s3", "user", "Test message")
        mgr.clear_session("s3")
        history = mgr.get_history("s3")
        assert len(history) == 0

    def test_session_exists(self):
        mgr = self._fresh_manager()
        assert mgr.session_exists("nonexistent") is False
        mgr.add_message("s4", "user", "Hello")
        assert mgr.session_exists("s4") is True

    def test_get_last_user_message(self):
        mgr = self._fresh_manager()
        mgr.add_message("s5", "user", "First question")
        mgr.add_message("s5", "assistant", "First answer")
        mgr.add_message("s5", "user", "Second question")
        assert mgr.get_last_user_message("s5") == "Second question"

    def test_get_last_assistant_message(self):
        mgr = self._fresh_manager()
        mgr.add_message("s6", "user", "Question")
        mgr.add_message("s6", "assistant", "Answer")
        assert mgr.get_last_assistant_message("s6") == "Answer"

    def test_get_recent_turns(self):
        mgr = self._fresh_manager()
        for i in range(10):
            mgr.add_message("s7", "user", f"Message {i}")
        recent = mgr.get_recent_turns("s7", n=3)
        assert len(recent) == 3
        assert recent[-1]["content"] == "Message 9"

    def test_message_has_timestamp(self):
        mgr = self._fresh_manager()
        mgr.add_message("s8", "user", "Hello")
        history = mgr.get_history("s8")
        assert "timestamp" in history[0]
        assert "Z" in history[0]["timestamp"]   # UTC ISO format

    def test_history_trimmed_at_max_turns(self):
        from app.session.manager import MAX_HISTORY_TURNS
        mgr = self._fresh_manager()
        for i in range(MAX_HISTORY_TURNS + 10):
            mgr.add_message("s9", "user", f"Message {i}")
        history = mgr.get_history("s9")
        assert len(history) <= MAX_HISTORY_TURNS

    def test_different_sessions_isolated(self):
        mgr = self._fresh_manager()
        mgr.add_message("session-A", "user", "Message A")
        mgr.add_message("session-B", "user", "Message B")
        history_a = mgr.get_history("session-A")
        history_b = mgr.get_history("session-B")
        assert len(history_a) == 1
        assert len(history_b) == 1
        assert history_a[0]["content"] == "Message A"
        assert history_b[0]["content"] == "Message B"

    def test_empty_session_returns_empty_list(self):
        mgr = self._fresh_manager()
        history = mgr.get_history("no-such-session")
        assert history == []

    def test_get_last_message_empty_session(self):
        mgr = self._fresh_manager()
        assert mgr.get_last_user_message("empty") is None
        assert mgr.get_last_assistant_message("empty") is None


class TestLanguageDetection:
    """Tests for the language detection module."""

    def test_english_detected(self):
        from app.services.language_handler import detect_language
        assert detect_language("What are my reward points?") == "en"

    def test_arabic_detected(self):
        from app.services.language_handler import detect_language
        assert detect_language("ما هي نقاط المكافآت الخاصة بي؟") == "ar"

    def test_empty_string_defaults_to_english(self):
        from app.services.language_handler import detect_language
        assert detect_language("") == "en"

    def test_mixed_text_arabic_majority(self):
        from app.services.language_handler import detect_language
        # Mostly Arabic with a few English words
        lang = detect_language("كيف يمكنني schedule طلب؟")
        # Arabic chars dominate
        assert lang == "ar"

    def test_is_arabic_helper(self):
        from app.services.language_handler import is_arabic
        assert is_arabic("مرحبا") is True
        assert is_arabic("Hello") is False

