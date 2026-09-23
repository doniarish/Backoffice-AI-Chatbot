"""
app/services/intent_classifier.py
-----------------------------------
LLM-based intent classifier for the Backoffice AI Chatbot demo.

Architecture pattern demonstrated:
  1. Fast-path keyword check (no LLM call for obvious greetings/small-talk)
  2. LLM classification with structured JSON output for complex intents
  3. Entity extraction alongside intent (dates, city, user_id)

Supported intents (10 generic demo intents):
  - greeting          : hello, hi, hey
  - small_talk        : casual conversation, how are you
  - out_of_scope      : unrelated to platform
  - general_faq       : policy / how-to questions (→ RAG)
  - check_rewards     : reward points balance / history
  - request_status    : check pickup request status
  - schedule_pickup   : book a new pickup
  - data_query        : ad-hoc analytical question (→ Text-to-SQL)
  - report_request    : generate a summary/PDF report
  - coverage_check    : check service area coverage

Entity extraction (when present):
  - city        : city name mentioned in query
  - user_id     : numeric user ID
  - start_date  : YYYY-MM-DD
  - end_date    : YYYY-MM-DD
  - category    : material category (Aluminium, Plastic, etc.)
"""

import json
import logging
import re
from typing import Dict, Any, Literal

logger = logging.getLogger(__name__)

IntentType = Literal[
    "greeting",
    "small_talk",
    "out_of_scope",
    "general_faq",
    "check_rewards",
    "request_status",
    "schedule_pickup",
    "data_query",
    "report_request",
    "coverage_check",
]

_EMPTY_ENTITIES: Dict[str, Any] = {
    "city": None,
    "user_id": None,
    "start_date": None,
    "end_date": None,
    "category": None,
}

# ── Fast-path keyword shortcuts ──────────────────────────────────────────────
# These avoid an LLM call for the most common, unambiguous patterns.

_GREETING_KEYWORDS = [
    "hi", "hello", "hey", "good morning", "good afternoon",
    "good evening", "assalam", "مرحبا", "السلام",
]

_SMALL_TALK_KEYWORDS = [
    "how are you", "how r u", "what's up", "who are you",
    "what can you do", "are you a bot", "كيف حالك",
]

_REWARDS_KEYWORDS = [
    "reward", "points", "redeem", "bonus", "نقاط", "مكافأة",
]

_STATUS_KEYWORDS = [
    "status", "my request", "my pickup", "pending", "cancelled",
    "completed", "track", "حالة", "طلبي",
]

_SCHEDULE_KEYWORDS = [
    "schedule", "book", "new pickup", "request pickup", "create request",
    "جدولة", "طلب جديد",
]

_DATA_KEYWORDS = [
    "how many", "total", "count", "show me", "list", "top", "compare",
    "average", "كم عدد", "إجمالي",
]

_REPORT_KEYWORDS = [
    "report", "pdf", "summary report", "generate report",
    "تقرير",
]

_COVERAGE_KEYWORDS = [
    "coverage", "service area", "my area", "zone", "district",
    "منطقة الخدمة",
]


def _quick_check(text: str):
    """
    Fast-path intent detection using keyword matching.
    Returns (intent, entities) if matched, or (None, None) if inconclusive.
    """
    q = text.lower().strip()

    # Very short greetings
    if len(q) < 50:
        for kw in _GREETING_KEYWORDS:
            if kw in q:
                return "greeting", dict(_EMPTY_ENTITIES)
        for kw in _SMALL_TALK_KEYWORDS:
            if kw in q:
                return "small_talk", dict(_EMPTY_ENTITIES)

    # Report check first (more specific than data_query)
    for kw in _REPORT_KEYWORDS:
        if kw in q:
            return "report_request", dict(_EMPTY_ENTITIES)

    for kw in _REWARDS_KEYWORDS:
        if kw in q:
            return "check_rewards", dict(_EMPTY_ENTITIES)

    for kw in _STATUS_KEYWORDS:
        if kw in q:
            return "request_status", dict(_EMPTY_ENTITIES)

    for kw in _SCHEDULE_KEYWORDS:
        if kw in q:
            return "schedule_pickup", dict(_EMPTY_ENTITIES)

    for kw in _DATA_KEYWORDS:
        if kw in q:
            return "data_query", dict(_EMPTY_ENTITIES)

    for kw in _COVERAGE_KEYWORDS:
        if kw in q:
            return "coverage_check", dict(_EMPTY_ENTITIES)

    return None, None


# ── LLM-based classification ─────────────────────────────────────────────────

_CLASSIFIER_PROMPT = """\
You are an intent classifier for a recycling platform backoffice chatbot.

Classify the user query into EXACTLY ONE of these intents:
  - "greeting"       : hello, hi, greetings
  - "small_talk"     : casual conversation (how are you, who are you, etc.)
  - "out_of_scope"   : unrelated to the recycling platform
  - "general_faq"    : policy, how-to, general platform questions (use RAG knowledge base)
  - "check_rewards"  : reward points balance, redemption, history
  - "request_status" : status of a specific pickup request
  - "schedule_pickup": book or schedule a new pickup request
  - "data_query"     : ad-hoc analytical question requiring a database query
  - "report_request" : generate a summary or PDF report
  - "coverage_check" : check if a location/area is covered by the service

Also extract entities if present:
  - city        : city name (string or null)
  - user_id     : numeric user ID (integer or null)
  - start_date  : YYYY-MM-DD (string or null)
  - end_date    : YYYY-MM-DD (string or null)
  - category    : material category e.g. Aluminium, Plastic (string or null)

Return ONLY valid JSON, no markdown:
{{"intent": "<intent>", "entities": {{"city": null, "user_id": null, "start_date": null, "end_date": null, "category": null}}}}

User query: {query}
"""


def classify_intent(query: str) -> Dict[str, Any]:
    """
    Classify the user query into an intent and extract entities.

    Args:
        query: raw user input (English or Arabic)

    Returns:
        dict with keys:
          - "intent"   : IntentType string
          - "entities" : dict of extracted entities

    Strategy:
        1. Run fast-path keyword check (no LLM cost)
        2. If inconclusive, call LLM for structured classification
        3. Fall back to "general_faq" if LLM fails
    """
    # Fast-path
    intent, entities = _quick_check(query)
    if intent:
        logger.debug("[IntentClassifier] fast-path → %s", intent)
        return {"intent": intent, "entities": entities}

    # LLM path
    try:
        from app.services.llm_service import llm
        prompt = _CLASSIFIER_PROMPT.format(query=query)
        response = llm.invoke(prompt)
        raw = response.content.strip()

        # Strip markdown code fences if present
        raw = re.sub(r"```(?:json)?", "", raw).strip()

        parsed = json.loads(raw)
        intent_val = parsed.get("intent", "general_faq")
        entities_val = parsed.get("entities", dict(_EMPTY_ENTITIES))

        # Ensure all entity keys exist
        for key in _EMPTY_ENTITIES:
            entities_val.setdefault(key, None)

        logger.info("[IntentClassifier] LLM → intent=%s entities=%s", intent_val, entities_val)
        return {"intent": intent_val, "entities": entities_val}

    except Exception as exc:
        logger.warning("[IntentClassifier] LLM failed (%s) → fallback general_faq", exc)
        return {"intent": "general_faq", "entities": dict(_EMPTY_ENTITIES)}

