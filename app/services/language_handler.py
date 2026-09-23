"""
app/services/language_handler.py
---------------------------------
Detects the language of a user query and normalises Arabic text if needed.

Demonstrates how a multilingual chatbot can transparently handle queries
in both English and Arabic.

Supported languages: English (en), Arabic (ar)
Default fallback: English
"""

import re
import logging
from typing import Literal

logger = logging.getLogger(__name__)

LanguageCode = Literal["en", "ar"]

# Unicode range for Arabic characters (Basic Arabic block: U+0600–U+06FF)
_ARABIC_PATTERN = re.compile(r"[\u0600-\u06FF]")

# Minimum fraction of characters that must be Arabic to classify as Arabic
_ARABIC_THRESHOLD = 0.25


def detect_language(text: str) -> LanguageCode:
    """
    Detect whether a query is primarily in Arabic or English.

    Strategy:
        Count the number of Arabic Unicode characters.
        If they account for >= ARABIC_THRESHOLD of non-space characters,
        classify the query as Arabic.

    Args:
        text: raw user input string

    Returns:
        "ar" if Arabic is detected, "en" otherwise
    """
    if not text or not text.strip():
        return "en"

    non_space = [c for c in text if not c.isspace()]
    if not non_space:
        return "en"

    arabic_chars = _ARABIC_PATTERN.findall(text)
    ratio = len(arabic_chars) / len(non_space)

    lang: LanguageCode = "ar" if ratio >= _ARABIC_THRESHOLD else "en"
    logger.debug(
        "[LanguageHandler] text=%.40r arabic_ratio=%.2f → lang=%s",
        text, ratio, lang
    )
    return lang


def get_response_language_instruction(lang: LanguageCode) -> str:
    """
    Return an LLM system instruction that enforces the response language.

    Args:
        lang: detected language code

    Returns:
        instruction string to prepend to LLM prompts
    """
    if lang == "ar":
        return (
            "IMPORTANT: The user wrote in Arabic. "
            "You MUST respond entirely in Arabic. "
            "Do not mix languages."
        )
    return (
        "The user wrote in English. Respond in clear, professional English."
    )


def is_arabic(text: str) -> bool:
    """Convenience function — returns True if the text is detected as Arabic."""
    return detect_language(text) == "ar"


# Example multilingual queries for demo/testing purposes
EXAMPLE_QUERIES = {
    "en": [
        "What are my reward points?",
        "How many completed requests do we have this month?",
        "Show me the top 5 users by weight collected.",
        "What materials are accepted for recycling?",
        "How do I cancel a pickup request?",
    ],
    "ar": [
        "ما هي نقاط المكافآت الخاصة بي؟",
        "كم عدد الطلبات المكتملة هذا الشهر؟",
        "أرني أفضل 5 مستخدمين حسب الوزن المجمع.",
        "ما هي المواد المقبولة لإعادة التدوير؟",
        "كيف يمكنني إلغاء طلب الاستلام؟",
    ],
}

