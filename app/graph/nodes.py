"""
app/graph/nodes.py
-------------------
LangGraph node functions for the Backoffice AI Chatbot demo workflow.

Each node is a Python function that:
  - Receives the current State dict
  - Performs one focused task
  - Returns a partial State update dict

Nodes defined here:
  classify_node      — detect language + classify intent + extract entities
  tool_node          — route to direct tool (rewards, coverage, status)
  rag_node           — retrieve from FAISS vector store and polish answer
  text_to_sql_node   — generate SQL, execute, and format results
  response_node      — assemble and finalize the response
  fallback_node      — handle greetings, small talk, out-of-scope
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


# ── classify_node ─────────────────────────────────────────────────────────────

def classify_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node 1: Language detection + Intent classification + Entity extraction.

    Reads:  state["user_message"]
    Writes: state["language"], state["intent"], state["entities"]
    """
    from app.services.language_handler import detect_language
    from app.services.intent_classifier import classify_intent

    query = state["user_message"]
    lang = detect_language(query)
    result = classify_intent(query)

    logger.info(
        "[Node:classify] lang=%s intent=%s entities=%s",
        lang, result["intent"], result["entities"]
    )

    return {
        "language": lang,
        "intent": result["intent"],
        "entities": result["entities"],
    }


# ── tool_node ─────────────────────────────────────────────────────────────────

def tool_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node 2: Direct tool execution (rewards, coverage, request status).

    Reads:  state["intent"], state["entities"]
    Writes: state["tool_result"], state["answer"] (if tool handled it)
    """
    from app.tools.router import route_to_tool
    from app.services.response_polisher import format_tool_result

    intent = state.get("intent", "")
    entities = state.get("entities", {})
    lang = state.get("language", "en")

    tool_result = route_to_tool(intent, entities)
    if tool_result is not None:
        answer = format_tool_result(tool_result, lang=lang)
        logger.info("[Node:tool] Tool handled intent='%s'", intent)
        return {
            "tool_result": tool_result,
            "answer": answer,
            "handled_by": "tool",
        }

    # No tool for this intent — signal to continue to RAG or Text-to-SQL
    return {"tool_result": None, "handled_by": None}


# ── rag_node ──────────────────────────────────────────────────────────────────

def rag_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node 3: RAG retrieval from the FAISS local vector store.

    Reads:  state["user_message"], state["language"]
    Writes: state["rag_context"], state["answer"]
    """
    from app.rag.pipeline import rag_pipeline
    from app.services.response_polisher import polish_rag_response

    query = state["user_message"]
    lang = state.get("language", "en")

    context = rag_pipeline.retrieve_context(query, k=3)
    answer = polish_rag_response(context, query, lang=lang)

    logger.info("[Node:rag] context_len=%d", len(context))
    return {
        "rag_context": context,
        "answer": answer,
        "handled_by": "rag",
    }


# ── text_to_sql_node ──────────────────────────────────────────────────────────

def text_to_sql_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node 4: Text-to-SQL pipeline — generates and executes a SQL query.

    Reads:  state["user_message"], state["entities"]
    Writes: state["sql_result"], state["sql_used"], state["answer"]
    """
    from app.text_to_sql.generator import generate_and_execute
    from app.services.response_polisher import format_sql_results

    query = state["user_message"]
    entities = state.get("entities", {})
    city_filter = entities.get("city")

    rows, sql_used, error = generate_and_execute(query, city_filter=city_filter)

    if error:
        logger.warning("[Node:text_to_sql] Error: %s", error)
        answer = f"I wasn't able to retrieve that data. ({error})"
    else:
        answer = format_sql_results(rows, sql_used, query)

    return {
        "sql_result": rows,
        "sql_used": sql_used,
        "answer": answer,
        "handled_by": "text_to_sql",
    }


# ── fallback_node ─────────────────────────────────────────────────────────────

def fallback_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node 5: Handle greetings, small talk, and out-of-scope queries.

    Returns canned (but friendly) responses without an LLM call.
    For small_talk, makes a lightweight LLM call to generate a natural reply.

    Reads:  state["intent"], state["language"], state["user_message"]
    Writes: state["answer"]
    """
    from app.services.response_polisher import build_out_of_scope_response

    intent = state.get("intent", "")
    lang = state.get("language", "en")
    query = state.get("user_message", "")

    if intent == "greeting":
        if lang == "ar":
            answer = "مرحباً! أنا مساعد منصة إعادة التدوير. كيف يمكنني مساعدتك اليوم؟"
        else:
            answer = (
                "Hello! I'm your recycling platform backoffice assistant. "
                "I can help you with pickup requests, reward points, "
                "service coverage, and platform analytics. How can I assist you?"
            )
        return {"answer": answer, "handled_by": "fallback"}

    if intent == "small_talk":
        try:
            from app.services.llm_service import llm
            prompt = (
                f"You are a helpful recycling platform assistant. "
                f"The user said: '{query}'. "
                f"Respond briefly and redirect them to platform-related help. "
                f"Do not reveal any technical details about your architecture."
            )
            response = llm.invoke(prompt)
            answer = response.content.strip()
        except Exception:
            answer = (
                "I'm doing great, thanks for asking! "
                "I'm here to help with your recycling pickups and rewards. "
                "What can I do for you?"
            )
        return {"answer": answer, "handled_by": "fallback"}

    # out_of_scope or anything else
    answer = build_out_of_scope_response(lang)
    return {"answer": answer, "handled_by": "fallback"}


# ── response_node ─────────────────────────────────────────────────────────────

def response_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node 6: Finalize and add RTL wrapping for Arabic responses.

    Reads:  state["answer"], state["language"]
    Writes: state["final_answer"]
    """
    answer = state.get("answer", "I'm sorry, I couldn't process your request.")
    lang = state.get("language", "en")

    if lang == "ar" and answer:
        final_answer = f"<div dir='rtl' style='text-align:right'>{answer}</div>"
    else:
        final_answer = answer

    return {"final_answer": final_answer}

