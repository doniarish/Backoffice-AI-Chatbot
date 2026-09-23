"""
app/graph/workflow.py
----------------------
LangGraph StateGraph definition for the Backoffice AI Chatbot demo.

Workflow overview:
                        ┌─────────────────┐
  User Query ──────────►│  classify_node  │
                        └────────┬────────┘
                                 │ intent + entities
                     ┌───────────▼───────────┐
                     │  should_use_tool?     │  ← conditional edge
                     └──┬────────────────┬──┘
                    YES │                │ NO
             ┌──────────▼──┐      ┌──────▼───────┐
             │  tool_node  │      │ route_intent │  ← conditional edge
             └──────────┬──┘      └──┬──────┬────┘
                        │      FAQ   │      │ data_query/report
                        │       ┌───▼──┐  ┌─▼──────────────┐
                        │       │  rag │  │ text_to_sql     │
                        │       └───┬──┘  └─┬──────────────┘
                        │           │        │
                        └─────┬─────┘────────┘
                              │ (all paths merge)
                        ┌─────▼────────┐
                        │ fallback or  │
                        │ response_node│
                        └─────┬────────┘
                              │
                           final_answer

State schema:
    user_message  : str           — raw user input
    session_id    : str           — unique session identifier
    language      : str           — "en" or "ar"
    intent        : str           — classified intent
    entities      : dict          — extracted entities
    tool_result   : dict | None   — result from direct tool call
    rag_context   : str | None    — retrieved context from FAISS
    sql_result    : list | None   — rows from Text-to-SQL execution
    sql_used      : str | None    — validated SQL that was run
    answer        : str | None    — intermediate answer
    handled_by    : str | None    — which node produced the answer
    final_answer  : str           — response to return to user
"""

import logging
from typing import Any, Dict, Optional, List
from typing_extensions import TypedDict

logger = logging.getLogger(__name__)

# ── State definition ──────────────────────────────────────────────────────────

class ChatState(TypedDict, total=False):
    user_message: str
    session_id: str
    language: str
    intent: str
    entities: Dict[str, Any]
    tool_result: Optional[Dict]
    rag_context: Optional[str]
    sql_result: Optional[List[Dict]]
    sql_used: Optional[str]
    answer: Optional[str]
    handled_by: Optional[str]
    final_answer: str


# ── Routing logic ─────────────────────────────────────────────────────────────

# Intents that should go directly to a tool (no RAG/SQL needed)
_TOOL_INTENTS = {"check_rewards", "coverage_check", "request_status", "report_request"}

# Intents that go to RAG (knowledge base Q&A)
_RAG_INTENTS = {"general_faq", "schedule_pickup"}

# Intents that go to Text-to-SQL (analytical queries)
_SQL_INTENTS = {"data_query"}

# Intents handled by the fallback node (no DB/LLM needed or only LLM)
_FALLBACK_INTENTS = {"greeting", "small_talk", "out_of_scope"}


def _route_after_classify(state: ChatState) -> str:
    """
    Conditional edge after classify_node.
    Returns the name of the next node to visit.
    """
    intent = state.get("intent", "general_faq")

    if intent in _TOOL_INTENTS:
        return "tool_node"
    if intent in _FALLBACK_INTENTS:
        return "fallback_node"
    if intent in _SQL_INTENTS:
        return "text_to_sql_node"
    # Default: FAQ / general_faq / anything else → RAG
    return "rag_node"


def _route_after_tool(state: ChatState) -> str:
    """
    Conditional edge after tool_node.
    If the tool handled the request, go to response_node.
    Otherwise, fall through to RAG.
    """
    if state.get("handled_by") == "tool":
        return "response_node"
    # Tool didn't handle it — route to RAG as fallback
    return "rag_node"


# ── Build the graph ───────────────────────────────────────────────────────────

def build_workflow():
    """
    Construct and compile the LangGraph StateGraph.

    Returns:
        Compiled LangGraph app with an `invoke(state)` method.
    """
    try:
        from langgraph.graph import StateGraph, END
    except ImportError as exc:
        raise ImportError(
            "langgraph is required. Run: pip install langgraph"
        ) from exc

    from app.graph.nodes import (
        classify_node,
        tool_node,
        rag_node,
        text_to_sql_node,
        fallback_node,
        response_node,
    )

    graph = StateGraph(ChatState)

    # ── Add nodes ──────────────────────────────────────────────────────────
    graph.add_node("classify_node",     classify_node)
    graph.add_node("tool_node",         tool_node)
    graph.add_node("rag_node",          rag_node)
    graph.add_node("text_to_sql_node",  text_to_sql_node)
    graph.add_node("fallback_node",     fallback_node)
    graph.add_node("response_node",     response_node)

    # ── Entry point ────────────────────────────────────────────────────────
    graph.set_entry_point("classify_node")

    # ── Conditional edges ──────────────────────────────────────────────────
    graph.add_conditional_edges(
        "classify_node",
        _route_after_classify,
        {
            "tool_node":        "tool_node",
            "rag_node":         "rag_node",
            "text_to_sql_node": "text_to_sql_node",
            "fallback_node":    "fallback_node",
        },
    )

    graph.add_conditional_edges(
        "tool_node",
        _route_after_tool,
        {
            "response_node": "response_node",
            "rag_node":      "rag_node",
        },
    )

    # ── Linear edges to response_node ─────────────────────────────────────
    graph.add_edge("rag_node",          "response_node")
    graph.add_edge("text_to_sql_node",  "response_node")
    graph.add_edge("fallback_node",     "response_node")

    # ── Terminal ───────────────────────────────────────────────────────────
    graph.add_edge("response_node", END)

    app = graph.compile()
    logger.info("[Workflow] LangGraph workflow compiled successfully.")
    return app


# Singleton — compiled once at module import
_workflow_app = None


def get_workflow():
    """Return the singleton compiled LangGraph workflow."""
    global _workflow_app
    if _workflow_app is None:
        _workflow_app = build_workflow()
    return _workflow_app


def run_chat(user_message: str, session_id: str = "default") -> Dict[str, Any]:
    """
    Convenience function: run a single chat turn through the full workflow.

    Args:
        user_message : raw user input string
        session_id   : unique session identifier

    Returns:
        Final state dict including 'final_answer' and metadata
    """
    from app.session.manager import session_manager

    # Add user message to session history
    session_manager.add_message(session_id, "user", user_message)

    initial_state: ChatState = {
        "user_message": user_message,
        "session_id": session_id,
        "language": "en",
        "intent": "",
        "entities": {},
        "tool_result": None,
        "rag_context": None,
        "sql_result": None,
        "sql_used": None,
        "answer": None,
        "handled_by": None,
        "final_answer": "",
    }

    workflow = get_workflow()
    final_state = workflow.invoke(initial_state)

    # Save assistant answer to session history
    final_answer = final_state.get("final_answer", "")
    session_manager.add_message(session_id, "assistant", final_answer)

    logger.info(
        "[Workflow] session=%s intent=%s handled_by=%s",
        session_id,
        final_state.get("intent"),
        final_state.get("handled_by"),
    )
    return final_state

