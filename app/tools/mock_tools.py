"""
app/tools/mock_tools.py
------------------------
Generic mock tool implementations for the Backoffice AI Chatbot demo.

These tools operate entirely on the local SQLite mock database.
No external APIs, no production systems, no real user data.

Tools provided:
    get_user_rewards(user_id)         — reward points summary for a user
    check_service_coverage(city)      — check if a city is in the service area
    get_request_status(request_id)    — status of a specific pickup request
    list_pending_requests(city)       — list pending requests in a city
    get_platform_summary()            — high-level platform metrics

Each tool returns a structured dict with:
    {
        "success": bool,
        "data": ...,
        "message": str       (human-readable summary)
    }
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Cities where the demo service operates
COVERED_CITIES = {"greenville", "maplewood", "lakeside"}


def get_user_rewards(user_id: int) -> dict:
    """
    Retrieve the reward points summary for a specific user.

    Args:
        user_id: the user's unique ID

    Returns:
        dict with total_earned, total_redeemed, balance, and breakdown by type
    """
    try:
        from demo.mock_database import get_connection
        conn = get_connection()

        # Check user exists
        user_row = conn.execute(
            "SELECT full_name, user_type FROM users WHERE user_id = ? AND is_active = 1",
            (user_id,)
        ).fetchone()

        if not user_row:
            return {
                "success": False,
                "data": None,
                "message": f"User ID {user_id} not found or inactive.",
            }

        # Aggregate rewards
        reward_rows = conn.execute(
            """
            SELECT reward_type,
                   SUM(points_earned)   AS earned,
                   SUM(points_redeemed) AS redeemed
            FROM rewards
            WHERE user_id = ?
            GROUP BY reward_type
            """,
            (user_id,)
        ).fetchall()

        conn.close()

        total_earned = sum(r["earned"] for r in reward_rows)
        total_redeemed = sum(r["redeemed"] for r in reward_rows)
        balance = total_earned - total_redeemed

        breakdown = {r["reward_type"]: {"earned": r["earned"], "redeemed": r["redeemed"]}
                     for r in reward_rows}

        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "user_name": user_row["full_name"],
                "total_earned": total_earned,
                "total_redeemed": total_redeemed,
                "balance": balance,
                "breakdown": breakdown,
            },
            "message": (
                f"{user_row['full_name']} has {balance} reward points "
                f"(earned: {total_earned}, redeemed: {total_redeemed})."
            ),
        }
    except Exception as exc:
        logger.error("[Tool:get_user_rewards] Error: %s", exc)
        return {"success": False, "data": None, "message": f"Error retrieving rewards: {exc}"}


def check_service_coverage(city: str) -> dict:
    """
    Check whether a given city is within the platform's service area.

    Args:
        city: city name to check (case-insensitive)

    Returns:
        dict indicating whether the city is covered and the list of covered cities
    """
    normalized = city.strip().lower()
    is_covered = normalized in COVERED_CITIES

    return {
        "success": True,
        "data": {
            "city": city,
            "is_covered": is_covered,
            "covered_cities": sorted(COVERED_CITIES),
        },
        "message": (
            f"'{city}' is {'within' if is_covered else 'NOT within'} the service coverage area. "
            f"Currently covered cities: {', '.join(sorted(COVERED_CITIES))}."
        ),
    }


def get_request_status(request_id: int) -> dict:
    """
    Retrieve the current status of a specific pickup request.

    Args:
        request_id: the request's unique ID

    Returns:
        dict with request details and status
    """
    try:
        from demo.mock_database import get_connection
        conn = get_connection()

        row = conn.execute(
            """
            SELECT r.request_id, r.status, r.category, r.weight_kg,
                   r.scheduled_at, r.completed_at, r.city,
                   u.full_name AS user_name
            FROM requests r
            JOIN users u ON u.user_id = r.user_id
            WHERE r.request_id = ?
            """,
            (request_id,)
        ).fetchone()
        conn.close()

        if not row:
            return {
                "success": False,
                "data": None,
                "message": f"Request ID {request_id} not found.",
            }

        data = dict(row)
        return {
            "success": True,
            "data": data,
            "message": (
                f"Request #{request_id} by {data['user_name']} "
                f"({data['category']}, {data['weight_kg']} kg) "
                f"is currently: {data['status']}."
            ),
        }
    except Exception as exc:
        logger.error("[Tool:get_request_status] Error: %s", exc)
        return {"success": False, "data": None, "message": f"Error: {exc}"}


def list_pending_requests(city: Optional[str] = None) -> dict:
    """
    List all pending pickup requests, optionally filtered by city.

    Args:
        city: optional city name filter (case-insensitive)

    Returns:
        dict with list of pending requests
    """
    try:
        from demo.mock_database import get_connection
        conn = get_connection()

        if city:
            rows = conn.execute(
                """
                SELECT r.request_id, r.category, r.weight_kg, r.scheduled_at, r.city,
                       u.full_name AS user_name
                FROM requests r JOIN users u ON u.user_id = r.user_id
                WHERE r.status = 'Pending' AND LOWER(r.city) = LOWER(?)
                ORDER BY r.scheduled_at
                LIMIT 50
                """,
                (city,)
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT r.request_id, r.category, r.weight_kg, r.scheduled_at, r.city,
                       u.full_name AS user_name
                FROM requests r JOIN users u ON u.user_id = r.user_id
                WHERE r.status = 'Pending'
                ORDER BY r.scheduled_at
                LIMIT 50
                """
            ).fetchall()

        conn.close()
        data = [dict(row) for row in rows]
        location_str = f" in {city}" if city else ""
        return {
            "success": True,
            "data": data,
            "message": f"Found {len(data)} pending request(s){location_str}.",
        }
    except Exception as exc:
        logger.error("[Tool:list_pending_requests] Error: %s", exc)
        return {"success": False, "data": None, "message": f"Error: {exc}"}


def get_platform_summary() -> dict:
    """
    Retrieve a high-level summary of platform metrics from the mock database.

    Returns:
        dict with user counts, request counts, and reward totals
    """
    try:
        from demo.mock_database import get_connection
        conn = get_connection()

        total_users = conn.execute(
            "SELECT COUNT(*) AS n FROM users WHERE is_active = 1"
        ).fetchone()["n"]

        status_rows = conn.execute(
            "SELECT status, COUNT(*) AS n FROM requests GROUP BY status"
        ).fetchall()
        status_counts = {row["status"]: row["n"] for row in status_rows}

        total_weight = conn.execute(
            "SELECT COALESCE(SUM(weight_kg), 0) AS total FROM requests WHERE status = 'Completed'"
        ).fetchone()["total"]

        reward_totals = conn.execute(
            "SELECT SUM(points_earned) AS earned, SUM(points_redeemed) AS redeemed FROM rewards"
        ).fetchone()

        conn.close()

        return {
            "success": True,
            "data": {
                "active_users": total_users,
                "requests": status_counts,
                "total_weight_collected_kg": round(total_weight, 2),
                "total_points_earned": reward_totals["earned"] or 0,
                "total_points_redeemed": reward_totals["redeemed"] or 0,
            },
            "message": (
                f"Platform has {total_users} active users, "
                f"{status_counts.get('Completed', 0)} completed pickups, "
                f"and {round(total_weight, 1)} kg total weight collected."
            ),
        }
    except Exception as exc:
        logger.error("[Tool:get_platform_summary] Error: %s", exc)
        return {"success": False, "data": None, "message": f"Error: {exc}"}

