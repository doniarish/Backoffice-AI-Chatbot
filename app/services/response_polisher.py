"""
app/services/response_polisher.py
-----------------------------------
Response polisher — post-processes answers to be natural and concise.

Demonstrates the pattern of:
  1. Context-only strict polishing for FAQ/RAG answers
  2. Tabular formatting for SQL result rows
  3. Direct passthrough for structured tool results

The polisher enforces a "context-only" rule: it will not inject
world knowledge that wasn't in the retrieved context.
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Sentinel token: LLM returns this when context doesn't contain the answer
_NO_ANSWER_SENTINEL = "NO_ANSWER_IN_CONTEXT"

_POLISH_PROMPT = """\
You are a helpful backoffice assistant for a recycling pickup platform.
A user asked a question and we retrieved relevant context from our knowledge base.

STRICT RULE: You may ONLY use facts from the Context below.
If the context does not answer the question, output exactly: {sentinel}
Do NOT invent facts, do NOT use world knowledge, keep the answer concise (2-4 sentences).

Context:
{context}

Question: {question}

Answer:""".format(sentinel=_NO_ANSWER_SENTINEL, context="{context}", question="{question}")

_FALLBACK_ANSWER = (
    "I'm sorry, I don't have specific information about that in my knowledge base. "
    "Please contact our support team for assistance."
)

_OUT_OF_SCOPE_ANSWER_EN = (
    "I'm your recycling platform assistant. I can help with pickup requests, "
    "reward points, service coverage, and platform analytics. "
    "How can I assist you today?"
)

_OUT_OF_SCOPE_ANSWER_AR = (
    "أنا مساعد منصة إعادة التدوير. يمكنني المساعدة في طلبات الاستلام، "
    "ونقاط المكافآت، وتغطية الخدمة، وتحليلات المنصة. "
    "كيف يمكنني مساعدتك اليوم؟"
)


def polish_rag_response(
    context: str,
    question: str,
    lang: str = "en",
) -> str:
    """
    Polish a RAG-retrieved context into a natural conversational answer.

    Args:
        context  : retrieved context string from the RAG pipeline
        question : original user question
        lang     : "en" or "ar" for response language

    Returns:
        Polished answer string
    """
    if not context or "No relevant information" in context:
        return _FALLBACK_ANSWER if lang == "en" else _OUT_OF_SCOPE_ANSWER_AR

    try:
        from app.services.llm_service import llm
        prompt = _POLISH_PROMPT.format(context=context, question=question)
        response = llm.invoke(prompt)
        answer = response.content.strip()

        if _NO_ANSWER_SENTINEL in answer:
            logger.debug("[ResponsePolisher] Sentinel detected — returning fallback.")
            return _FALLBACK_ANSWER if lang == "en" else _OUT_OF_SCOPE_ANSWER_AR

        return answer
    except Exception as exc:
        logger.warning("[ResponsePolisher] LLM polish failed (%s) — returning raw context.", exc)
        # Return first 400 chars of context as fallback
        return context[:400].strip()


def format_sql_results(
    rows: List[Dict[str, Any]],
    sql_used: str,
    question: str,
) -> str:
    """
    Format SQL query results as a human-readable markdown table + summary.

    Args:
        rows     : list of result dicts from the DB
        sql_used : the SQL that was executed (for transparency)
        question : original user question

    Returns:
        Formatted string response
    """
    if not rows:
        return "The query returned no results for your question."

    # Build markdown table
    columns = list(rows[0].keys())
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    table_rows = [
        "| " + " | ".join(str(row.get(col, "")) for col in columns) + " |"
        for row in rows[:50]   # Cap at 50 rows in display
    ]

    table = "\n".join([header, separator] + table_rows)

    count_note = f"\n\n*Showing {len(rows)} result(s).*" if len(rows) > 0 else ""
    return f"{table}{count_note}"


def format_tool_result(result: dict, lang: str = "en") -> str:
    """
    Format a tool result dict into a human-readable answer.

    Args:
        result : dict with keys: success, data, message
        lang   : "en" or "ar"

    Returns:
        Human-readable string
    """
    if not result.get("success"):
        return result.get("message", "An error occurred processing your request.")
    return result.get("message", "Done.")


def build_out_of_scope_response(lang: str = "en") -> str:
    """Return a polite out-of-scope redirect message in the detected language."""
    return _OUT_OF_SCOPE_ANSWER_AR if lang == "ar" else _OUT_OF_SCOPE_ANSWER_EN

