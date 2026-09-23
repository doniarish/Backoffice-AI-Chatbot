"""
app/api/routes.py
------------------
FastAPI route definitions for the Backoffice AI Chatbot demo.

Endpoints:
    POST /chat           — main chat endpoint
    GET  /health         — health check
    GET  /session/{id}   — retrieve session conversation history
    DELETE /session/{id} — clear session history
"""

import uuid
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Request / Response models ─────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Incoming chat request payload."""
    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    session_id: Optional[str] = Field(
        default=None,
        description="Session ID for multi-turn context. Auto-generated if not provided."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "message": "What are my reward points for user 1?",
                "session_id": "demo-session-001",
            }
        }


class ChatResponse(BaseModel):
    """Chat endpoint response envelope."""
    success: bool
    answer: str
    session_id: str
    intent: Optional[str] = None
    handled_by: Optional[str] = None
    language: Optional[str] = None
    error: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "answer": "User 1 (Alice Morgan) has 310 reward points.",
                "session_id": "demo-session-001",
                "intent": "check_rewards",
                "handled_by": "tool",
                "language": "en",
                "error": None,
            }
        }


# ── POST /chat ────────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse, summary="Send a chat message")
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Main chat endpoint.

    Processes the user message through the full LangGraph workflow:
      1. Language detection
      2. Intent classification
      3. Route to: Tool / RAG / Text-to-SQL / Fallback
      4. Assemble and return the final answer

    All data is sourced from the local mock database — no external APIs or
    production systems are accessed.
    """
    # Auto-generate session ID if not provided
    session_id = request.session_id or str(uuid.uuid4())

    try:
        from app.graph.workflow import run_chat
        state = run_chat(
            user_message=request.message,
            session_id=session_id,
        )

        return ChatResponse(
            success=True,
            answer=state.get("final_answer", "I'm sorry, I couldn't process your request."),
            session_id=session_id,
            intent=state.get("intent"),
            handled_by=state.get("handled_by"),
            language=state.get("language", "en"),
            error=None,
        )

    except Exception as exc:
        logger.error("[API:/chat] Unexpected error: %s", exc, exc_info=True)
        return ChatResponse(
            success=False,
            answer="An internal error occurred. Please try again.",
            session_id=session_id,
            error=str(exc),
        )


# ── GET /health ───────────────────────────────────────────────────────────────

@router.get("/health", summary="Health check")
async def health() -> dict:
    """
    Health check endpoint.

    Returns basic system status — confirms the API is running.
    Does not check external service connectivity in the demo.
    """
    return {
        "status": "ok",
        "service": "Backoffice AI Chatbot Demo",
        "version": "1.0.0",
    }


# ── GET /session/{session_id} ─────────────────────────────────────────────────

@router.get("/session/{session_id}", summary="Get session history")
async def get_session(session_id: str) -> dict:
    """
    Retrieve the full conversation history for a session.

    Returns a list of message dicts with role, content, and timestamp.
    """
    try:
        from app.session.manager import session_manager
        history = session_manager.get_history(session_id)
        return {
            "session_id": session_id,
            "message_count": len(history),
            "history": history,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── DELETE /session/{session_id} ──────────────────────────────────────────────

@router.delete("/session/{session_id}", summary="Clear session history")
async def clear_session(session_id: str) -> dict:
    """
    Clear all conversation history for a given session.
    This cannot be undone.
    """
    try:
        from app.session.manager import session_manager
        session_manager.clear_session(session_id)
        return {"success": True, "session_id": session_id, "message": "Session cleared."}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

