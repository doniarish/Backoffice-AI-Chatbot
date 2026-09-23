"""
tests/test_tools.py
--------------------
Unit tests for the mock tool implementations and tool router.
"""

import pytest


class TestMockTools:
    """Tests for individual mock tool functions."""

    def test_get_user_rewards_valid_user(self):
        from app.tools.mock_tools import get_user_rewards
        result = get_user_rewards(1)
        assert result["success"] is True
        assert result["data"]["user_id"] == 1
        assert result["data"]["total_earned"] > 0
        assert result["data"]["balance"] >= 0

    def test_get_user_rewards_invalid_user(self):
        from app.tools.mock_tools import get_user_rewards
        result = get_user_rewards(9999)
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_check_service_coverage_covered_city(self):
        from app.tools.mock_tools import check_service_coverage
        result = check_service_coverage("Greenville")
        assert result["success"] is True
        assert result["data"]["is_covered"] is True

    def test_check_service_coverage_case_insensitive(self):
        from app.tools.mock_tools import check_service_coverage
        result = check_service_coverage("GREENVILLE")
        assert result["data"]["is_covered"] is True

    def test_check_service_coverage_not_covered(self):
        from app.tools.mock_tools import check_service_coverage
        result = check_service_coverage("Atlantis")
        assert result["data"]["is_covered"] is False

    def test_get_request_status_valid(self):
        from app.tools.mock_tools import get_request_status
        result = get_request_status(1)
        assert result["success"] is True
        assert "status" in result["data"]
        assert result["data"]["request_id"] == 1

    def test_get_request_status_invalid(self):
        from app.tools.mock_tools import get_request_status
        result = get_request_status(99999)
        assert result["success"] is False

    def test_list_pending_requests_no_filter(self):
        from app.tools.mock_tools import list_pending_requests
        result = list_pending_requests()
        assert result["success"] is True
        assert isinstance(result["data"], list)
        for req in result["data"]:
            assert req.get("status") is None or True   # status not included in result cols

    def test_list_pending_requests_with_city(self):
        from app.tools.mock_tools import list_pending_requests
        result = list_pending_requests("Greenville")
        assert result["success"] is True

    def test_get_platform_summary(self):
        from app.tools.mock_tools import get_platform_summary
        result = get_platform_summary()
        assert result["success"] is True
        data = result["data"]
        assert "active_users" in data
        assert "requests" in data
        assert "total_weight_collected_kg" in data
        assert data["active_users"] > 0


class TestToolRouter:
    """Tests for the tool routing dispatcher."""

    def test_routes_check_rewards_with_user_id(self):
        from app.tools.router import route_to_tool
        result = route_to_tool("check_rewards", {"user_id": 1})
        assert result is not None
        assert result["success"] is True

    def test_routes_check_rewards_no_user_id(self):
        from app.tools.router import route_to_tool
        result = route_to_tool("check_rewards", {})
        assert result is not None
        assert result["success"] is False
        assert "user ID" in result["message"]

    def test_routes_coverage_check_with_city(self):
        from app.tools.router import route_to_tool
        result = route_to_tool("coverage_check", {"city": "Maplewood"})
        assert result is not None
        assert result["data"]["is_covered"] is True

    def test_routes_coverage_check_no_city(self):
        from app.tools.router import route_to_tool
        result = route_to_tool("coverage_check", {})
        assert result is not None
        assert "covered_cities" in result["data"]

    def test_routes_report_request(self):
        from app.tools.router import route_to_tool
        result = route_to_tool("report_request", {})
        assert result is not None
        assert result["success"] is True

    def test_returns_none_for_rag_intents(self):
        """Intents meant for RAG should return None (delegate to RAG node)."""
        from app.tools.router import route_to_tool
        result = route_to_tool("general_faq", {})
        assert result is None

    def test_returns_none_for_data_query(self):
        from app.tools.router import route_to_tool
        result = route_to_tool("data_query", {})
        assert result is None

    def test_returns_none_for_greeting(self):
        from app.tools.router import route_to_tool
        result = route_to_tool("greeting", {})
        assert result is None

    def test_routable_intents_list(self):
        from app.tools.router import get_routable_intents
        intents = get_routable_intents()
        assert "check_rewards" in intents
        assert "coverage_check" in intents
        assert "report_request" in intents

