"""
app/session/manager.py
----------------------
Session context manager for multi-turn conversation history.

Strategy:
  1. Attempt to connect to Redis (if REDIS_URL is set in .env).
  2. Fall back to a thread-safe in-memory dictionary if Redis is unavailable.

This demonstrates the session/context pattern without requiring a production
Redis instance. Set REDIS_URL in .env to enable persistent sessions.

Example:
    from app.session.manager import session_manager

    session_manager.add_message("session-abc", "user", "Hello!")
    history = session_manager.get_history("session-abc")
"""

import json
import logging
import threading
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Max conversation turns stored per session
MAX_HISTORY_TURNS = 20
# Session TTL in seconds (1 hour)
SESSION_TTL = 3600


class InMemorySessionStore:
    """
    Thread-safe in-memory session store.
    Used as a fallback when Redis is unavailable.
    Data is lost on process restart — suitable for demo/development only.
    """

    def __init__(self):
        self._store: Dict[str, List[Dict]] = {}
        self._lock = threading.Lock()

    def get(self, session_id: str) -> List[Dict]:
        with self._lock:
            return list(self._store.get(session_id, []))

    def set(self, session_id: str, history: List[Dict]) -> None:
        with self._lock:
            self._store[session_id] = history[-MAX_HISTORY_TURNS:]

    def delete(self, session_id: str) -> None:
        with self._lock:
            self._store.pop(session_id, None)

    def exists(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._store

    def list_sessions(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())


class RedisSessionStore:
    """
    Redis-backed session store for persistent multi-turn context.
    Each session is stored as a JSON list under the key `chat:{session_id}`.
    """

    def __init__(self, redis_url: str):
        import redis
        self._client = redis.from_url(redis_url, decode_responses=True)
        logger.info("[Session] Connected to Redis at %s", redis_url)

    def _key(self, session_id: str) -> str:
        return f"chat:{session_id}"

    def get(self, session_id: str) -> List[Dict]:
        raw = self._client.get(self._key(session_id))
        if raw:
            return json.loads(raw)
        return []

    def set(self, session_id: str, history: List[Dict]) -> None:
        trimmed = history[-MAX_HISTORY_TURNS:]
        self._client.setex(
            self._key(session_id),
            SESSION_TTL,
            json.dumps(trimmed)
        )

    def delete(self, session_id: str) -> None:
        self._client.delete(self._key(session_id))

    def exists(self, session_id: str) -> bool:
        return bool(self._client.exists(self._key(session_id)))

    def list_sessions(self) -> List[str]:
        keys = self._client.keys("chat:*")
        return [k.replace("chat:", "") for k in keys]


class SessionManager:
    """
    Public interface for session management.

    Automatically selects Redis or in-memory backend based on REDIS_URL env var.

    Usage:
        session_manager.add_message(session_id, role, content)
        history = session_manager.get_history(session_id)
        session_manager.clear_session(session_id)
    """

    def __init__(self):
        self._store = self._init_store()

    def _init_store(self):
        import os
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                store = RedisSessionStore(redis_url)
                # Test the connection
                store._client.ping()
                logger.info("[Session] Using Redis backend.")
                return store
            except Exception as exc:
                logger.warning(
                    "[Session] Redis unavailable (%s). Falling back to in-memory store.", exc
                )
        logger.info("[Session] Using in-memory session store (no persistence).")
        return InMemorySessionStore()

    def get_history(self, session_id: str) -> List[Dict]:
        """
        Retrieve the full conversation history for a session.

        Returns a list of message dicts:
            [{"role": "user"|"assistant", "content": "...", "timestamp": "..."}]
        """
        return self._store.get(session_id)

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """
        Append a message to the session history.

        Args:
            session_id : unique session identifier
            role       : "user" or "assistant"
            content    : message text
        """
        history = self._store.get(session_id)
        history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })
        self._store.set(session_id, history)
        logger.debug("[Session] %s → added %s message (total: %d)", session_id, role, len(history))

    def clear_session(self, session_id: str) -> None:
        """Clear all conversation history for a session."""
        self._store.delete(session_id)
        logger.info("[Session] %s → cleared.", session_id)

    def session_exists(self, session_id: str) -> bool:
        """Check if a session has any history."""
        return self._store.exists(session_id)

    def get_last_user_message(self, session_id: str) -> Optional[str]:
        """Return the most recent user message content, or None."""
        history = self.get_history(session_id)
        for msg in reversed(history):
            if msg.get("role") == "user":
                return msg.get("content")
        return None

    def get_last_assistant_message(self, session_id: str) -> Optional[str]:
        """Return the most recent assistant message content, or None."""
        history = self.get_history(session_id)
        for msg in reversed(history):
            if msg.get("role") == "assistant":
                return msg.get("content")
        return None

    def get_recent_turns(self, session_id: str, n: int = 6) -> List[Dict]:
        """Return the last N messages from the session history."""
        history = self.get_history(session_id)
        return history[-n:]


# Singleton instance — import and use directly throughout the app
session_manager = SessionManager()

