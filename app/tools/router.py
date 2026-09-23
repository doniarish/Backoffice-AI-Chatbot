"""
app/tools/router.py
--------------------
Tool routing dispatcher for the Backoffice AI Chatbot demo.

Demonstrates the pattern of mapping an intent to a specific tool
and dispatching with extracted entities from the intent classifier.

Supported intent → tool mappings:
    check_rewards    → get_user_rewards
    coverage_check   → check_service_coverage
    request_status   → get_request_status
    report_request   → get_platform_summary (demo simplified)

For intents not handled by a direct tool (general_faq, data_query, etc.),
the router returns None and the LangGraph orchestrator routes to RAG or Text-to-SQL.
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Map from intent → (tool_function_name, required_entity_key)
_TOOL_ROUTING_MAP: Dict[str, str] = {
    "check_rewards":  "get_user_rewards",
    "coverage_check": "check_service_coverage",
    "request_status": "get_request_status",
    "report_request": "get_platform_summary",
}


def route_to_tool(intent: str, entities: Dict[str, Any]) -> Optional[dict]:
    """
    Dispatch an intent to the appropriate mock tool and return the result.

    Args:
        intent   : classified intent string
        entities : extracted entities dict from the intent classifier

    Returns:
        Tool result dict if a tool was found and executed.
        None if the intent should be handled by RAG or Text-to-SQL instead.
    """
    from app.tools.mock_tools import (
        get_user_rewards,
        check_service_coverage,
        get_request_status,
        get_platform_summary,
        list_pending_requests,
    )

    logger.info("[ToolRouter] intent=%s entities=%s", intent, entities)

    if intent == "check_rewards":
        user_id = entities.get("user_id")
        if user_id:
            return get_user_rewards(int(user_id))
        return {
            "success": False,
            "data": None,
            "message": "Please provide a user ID to check reward points. Example: 'reward points for user 1'",
        }

    if intent == "coverage_check":
        city = entities.get("city") or ""
        if city:
            return check_service_coverage(city)
        return {
            "success": True,
            "data": {"covered_cities": ["Greenville", "Maplewood", "Lakeside"]},
            "message": "Our service currently covers: Greenville, Maplewood, and Lakeside.",
        }

    if intent == "request_status":
        # Try to get request_id from entities
        request_id = entities.get("request_id") or entities.get("user_id")
        if request_id:
            return get_request_status(int(request_id))
        city = entities.get("city")
        return list_pending_requests(city)

    if intent == "report_request":
        return get_platform_summary()

    # Intent not handled by a direct tool → return None → route to RAG / Text-to-SQL
    logger.debug("[ToolRouter] No tool for intent='%s' — delegating to RAG/Text2SQL", intent)
    return None


def get_routable_intents() -> list:
    """Return the list of intents that have a direct tool mapping."""
    return list(_TOOL_ROUTING_MAP.keys())

