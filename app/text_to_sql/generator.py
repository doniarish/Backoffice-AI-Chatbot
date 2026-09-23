"""
app/text_to_sql/generator.py
-----------------------------
Text-to-SQL pipeline for the Backoffice AI Chatbot demo.

Pipeline:
  1. Build prompt  — assemble schema + few-shot examples + user question
  2. Generate SQL  — LLM produces a SELECT statement
  3. Validate SQL  — syntax + semantic safety guardrails
  4. Execute SQL   — run against local SQLite mock database (read-only)
  5. Return result — (rows, sql_used, error_message)

Uses SQLite (demo_data.db) — NO connection to any production database.
All data is entirely fictional.

Schema (see demo/mock_database.py):
    users    (user_id, full_name, user_type, city, is_active, registered_at)
    requests (request_id, user_id, city, status, category, weight_kg, scheduled_at, completed_at)
    rewards  (reward_id, user_id, points_earned, points_redeemed, reward_type, created_at)
"""

import logging
from datetime import date
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

MAX_ROWS = 100
MAX_RETRIES = 2

# ── Schema context for LLM prompt ────────────────────────────────────────────

SCHEMA_DESCRIPTION = """
You have READ-ONLY access to a SQLite database with three tables:

TABLE: users
  user_id       INTEGER  — unique user identifier
  full_name     TEXT     — user's display name
  user_type     TEXT     — 'Domestic', 'Corporate', or 'Collector'
  city          TEXT     — city name (e.g. 'Greenville', 'Maplewood', 'Lakeside')
  is_active     INTEGER  — 1 = active account, 0 = deactivated
  registered_at TEXT     — registration date (YYYY-MM-DD)

TABLE: requests
  request_id    INTEGER  — unique request identifier
  user_id       INTEGER  — references users.user_id
  city          TEXT     — city where pickup was requested
  status        TEXT     — 'Completed', 'Pending', 'Cancelled', or 'Expired'
  category      TEXT     — material type: 'Aluminium', 'Copper', 'Plastic', 'Paper', 'Steel', 'Glass'
  weight_kg     REAL     — weight of material collected in kilograms
  scheduled_at  TEXT     — scheduled pickup datetime (YYYY-MM-DD HH:MM)
  completed_at  TEXT     — actual completion datetime (NULL if not completed)

TABLE: rewards
  reward_id       INTEGER — unique reward record identifier
  user_id         INTEGER — references users.user_id
  points_earned   INTEGER — points earned in this transaction
  points_redeemed INTEGER — points redeemed in this transaction
  reward_type     TEXT    — 'signup_bonus', 'business', 'referral', or 'promotion'
  created_at      TEXT    — record date (YYYY-MM-DD)
"""

FEW_SHOT_EXAMPLES = [
    {
        "question": "How many active users are there?",
        "sql": "SELECT COUNT(*) AS active_users FROM users WHERE is_active = 1;"
    },
    {
        "question": "What is the total weight collected in Greenville?",
        "sql": (
            "SELECT SUM(weight_kg) AS total_weight_kg "
            "FROM requests "
            "WHERE city = 'Greenville' AND status = 'Completed';"
        )
    },
    {
        "question": "Show me the top 5 users by completed pickups.",
        "sql": (
            "SELECT u.full_name, COUNT(r.request_id) AS completed_orders "
            "FROM users u "
            "JOIN requests r ON r.user_id = u.user_id "
            "WHERE r.status = 'Completed' "
            "GROUP BY u.user_id, u.full_name "
            "ORDER BY completed_orders DESC "
            "LIMIT 5;"
        )
    },
    {
        "question": "How many corporate users are registered?",
        "sql": (
            "SELECT COUNT(*) AS corporate_users "
            "FROM users "
            "WHERE user_type = 'Corporate' AND is_active = 1;"
        )
    },
    {
        "question": "What is the total reward points balance across all users?",
        "sql": (
            "SELECT SUM(points_earned - points_redeemed) AS total_balance_points "
            "FROM rewards;"
        )
    },
    {
        "question": "How many cancelled requests are there?",
        "sql": "SELECT COUNT(*) AS cancelled_requests FROM requests WHERE status = 'Cancelled';"
    },
    {
        "question": "Which city has the highest total weight collected?",
        "sql": (
            "SELECT city, SUM(weight_kg) AS total_kg "
            "FROM requests "
            "WHERE status = 'Completed' "
            "GROUP BY city "
            "ORDER BY total_kg DESC "
            "LIMIT 1;"
        )
    },
    {
        "question": "List all users from Maplewood.",
        "sql": (
            "SELECT user_id, full_name, user_type, registered_at "
            "FROM users "
            "WHERE city = 'Maplewood' AND is_active = 1 "
            "LIMIT 100;"
        )
    },
]


def _format_few_shots() -> str:
    """Format few-shot examples into the LLM prompt block."""
    lines = ["EXAMPLE QUERIES (use these patterns as guidance):"]
    for i, ex in enumerate(FEW_SHOT_EXAMPLES, 1):
        lines.append(f"\nExample {i}:")
        lines.append(f"  Question: {ex['question']}")
        lines.append(f"  SQL: {ex['sql']}")
    return "\n".join(lines)


def _build_prompt(question: str, city_filter: Optional[str] = None) -> str:
    """
    Build the full prompt for the SQL generation LLM call.

    Includes: today's date, schema, few-shot examples, strict read-only rules, and the user question.
    """
    today = date.today().isoformat()
    city_note = ""
    if city_filter:
        city_note = (
            f"\nSCOPE: The user has access only to city '{city_filter}'. "
            f"ALWAYS add WHERE city = '{city_filter}' (or equivalent JOIN filter) to every query.\n"
        )

    few_shots = _format_few_shots()

    return f"""You are a SQL expert for a recycling pickup analytics platform.
You have READ-ONLY access to a SQLite database. This is strictly enforced.

TODAY'S DATE: {today}
{city_note}
{SCHEMA_DESCRIPTION}

{few_shots}

=== STRICT RULES — NEVER VIOLATE ===
1. Generate ONLY a SELECT statement (or WITH ... SELECT for CTEs). Nothing else.
2. NEVER use: INSERT, UPDATE, DELETE, MERGE, DROP, TRUNCATE, ALTER, CREATE
3. NEVER use: EXEC, EXECUTE, PRAGMA, ATTACH, DETACH
4. NEVER expose sensitive columns: password, national_id, bank_account
5. Always use LIMIT {MAX_ROWS} for row-level queries. Aggregates (COUNT, SUM) do not need LIMIT.
6. Use standard SQLite syntax (no SQL Server syntax like TOP, GETDATE, DATEADD).
7. For dates use: DATE('now'), DATE('now', '-30 days'), strftime('%Y-%m', date_col), etc.
8. Return ONLY the SQL — no explanation, no markdown, no code fences.
=== END RULES ===

User question: {question}

SQL:"""


def generate_and_execute(
    question: str,
    city_filter: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], str, str]:
    """
    Run the full Text-to-SQL pipeline:
      1. Build prompt
      2. Generate SQL via LLM
      3. Validate SQL (safety + syntax)
      4. Execute against SQLite mock database
      5. Return results

    Args:
        question    : natural language question from the user
        city_filter : optional city name to scope the query (role-based access)

    Returns:
        Tuple of:
          - rows          : list of result dicts [{col: value, ...}]
          - sql_used      : the validated SQL that was executed
          - error_message : empty string on success; description on failure
    """
    from app.text_to_sql.validator import validate_sql
    from demo.mock_database import get_connection

    prompt = _build_prompt(question, city_filter)

    # ── LLM SQL generation (with retries) ─────────────────────────────────
    raw_sql = ""
    last_error = ""

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            from app.services.llm_service import llm
            response = llm.invoke(prompt)
            raw_sql = response.content.strip()
            logger.info("[Text2SQL] Attempt %d: generated SQL (%.60s...)", attempt, raw_sql)
        except Exception as exc:
            last_error = f"LLM call failed: {exc}"
            logger.warning("[Text2SQL] LLM error on attempt %d: %s", attempt, exc)
            continue

        # ── Validate ───────────────────────────────────────────────────────
        is_valid, clean_sql, validation_error = validate_sql(raw_sql)
        if not is_valid:
            last_error = validation_error
            logger.warning("[Text2SQL] Validation failed (attempt %d): %s", attempt, validation_error)
            # Inject the error into prompt for retry
            prompt += f"\n\n[Previous attempt failed validation: {validation_error}. Fix and regenerate.]\n\nSQL:"
            continue

        # ── Execute ────────────────────────────────────────────────────────
        try:
            conn = get_connection()
            cursor = conn.execute(clean_sql)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
            conn.close()
            logger.info("[Text2SQL] Executed successfully. Rows returned: %d", len(rows))
            return rows, clean_sql, ""
        except Exception as db_exc:
            last_error = f"SQL execution error: {db_exc}"
            logger.warning("[Text2SQL] DB error (attempt %d): %s", attempt, db_exc)
            prompt += f"\n\n[Previous SQL caused DB error: {db_exc}. Fix and regenerate.]\n\nSQL:"

    # All retries exhausted
    logger.error("[Text2SQL] All %d attempts failed. Last error: %s", MAX_RETRIES, last_error)
    return [], raw_sql, last_error

