"""
app/text_to_sql/validator.py
-----------------------------
SQL safety validator for the Text-to-SQL demo pipeline.

Two-layer validation:
  Layer 1 — Syntax check  : strip SQL cleanly, ensure it starts with SELECT/WITH
  Layer 2 — Semantic check: block forbidden DML keywords and sensitive columns

This is a simplified demonstration of the guardrail pattern used in production
Text-to-SQL systems to prevent SQL injection or accidental data modification.

Rules enforced:
  - Query MUST start with SELECT or WITH (CTEs allowed)
  - Forbidden DML: INSERT, UPDATE, DELETE, MERGE, DROP, TRUNCATE, ALTER, CREATE
  - Forbidden exec: EXEC, EXECUTE, SP_EXECUTESQL, OPENROWSET, XP_CMDSHELL
  - Forbidden PII columns: password, password_hash, national_id, bank_account
  - Query MUST reference at least one allowed table
"""

import re
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)

# ── Allowed tables (demo SQLite schema) ─────────────────────────────────────
ALLOWED_TABLES: List[str] = ["users", "requests", "rewards"]

# ── Forbidden keywords (DML + dangerous exec commands) ──────────────────────
FORBIDDEN_KEYWORDS: List[str] = [
    "INSERT", "UPDATE", "DELETE", "MERGE", "DROP", "TRUNCATE",
    "ALTER", "CREATE", "EXEC", "EXECUTE", "SP_EXECUTESQL",
    "OPENROWSET", "XP_CMDSHELL", "ATTACH", "DETACH",
    "PRAGMA",   # SQLite-specific admin command
]

# ── Forbidden column patterns (PII protection) ───────────────────────────────
FORBIDDEN_COLUMNS: List[str] = [
    "password", "password_hash", "national_id", "bank_account",
    "iban", "credit_card", "ssn",
]


def _strip_sql(raw: str) -> str:
    """
    Extract clean SQL from LLM output.
    Removes markdown code fences (```sql ... ```) and leading/trailing whitespace.
    """
    raw = re.sub(r"```(?:sql)?", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"```", "", raw)
    return raw.strip()


def _check_forbidden_keywords(sql: str) -> List[str]:
    """Return list of forbidden keywords found in the SQL (case-insensitive)."""
    found = []
    upper_sql = sql.upper()
    for kw in FORBIDDEN_KEYWORDS:
        # Word-boundary match to avoid false positives (e.g. "SELECT" inside "SELECTED")
        if re.search(rf"\b{re.escape(kw)}\b", upper_sql):
            found.append(kw)
    return found


def _check_forbidden_columns(sql: str) -> List[str]:
    """Return list of forbidden PII column patterns found (case-insensitive)."""
    found = []
    lower_sql = sql.lower()
    for col in FORBIDDEN_COLUMNS:
        if re.search(rf"\b{re.escape(col)}\b", lower_sql):
            found.append(col)
    return found


def _check_allowed_tables(sql: str) -> bool:
    """Return True if at least one allowed table is referenced in the SQL."""
    lower_sql = sql.lower()
    return any(table in lower_sql for table in ALLOWED_TABLES)


def validate_sql(raw_sql: str) -> Tuple[bool, str, str]:
    """
    Validate a raw SQL string for safety and correctness.

    Args:
        raw_sql: the SQL string (possibly wrapped in markdown fences)

    Returns:
        Tuple of (is_valid: bool, clean_sql: str, error_message: str)
        - is_valid      : True if SQL passed all checks
        - clean_sql     : stripped, clean SQL string
        - error_message : empty string if valid; description of failure if invalid
    """
    # Step 1: Strip markdown fences
    sql = _strip_sql(raw_sql)

    if not sql:
        return False, "", "Empty SQL generated."

    # Step 2: Must start with SELECT or WITH (for CTEs)
    first_token = sql.lstrip().upper().split()[0] if sql.strip() else ""
    if first_token not in ("SELECT", "WITH"):
        return (
            False, sql,
            f"SQL must start with SELECT or WITH. Got: '{first_token}'. "
            "Only read-only SELECT queries are permitted."
        )

    # Step 3: Check for forbidden DML/exec keywords
    forbidden_found = _check_forbidden_keywords(sql)
    if forbidden_found:
        return (
            False, sql,
            f"SQL contains forbidden keyword(s): {', '.join(forbidden_found)}. "
            "Only read-only SELECT statements are allowed."
        )

    # Step 4: Check for PII column access
    pii_found = _check_forbidden_columns(sql)
    if pii_found:
        return (
            False, sql,
            f"SQL references forbidden PII column(s): {', '.join(pii_found)}. "
            "These columns are not accessible via the chat interface."
        )

    # Step 5: Must reference at least one known table
    if not _check_allowed_tables(sql):
        return (
            False, sql,
            f"SQL does not reference any known tables. "
            f"Allowed tables: {', '.join(ALLOWED_TABLES)}."
        )

    logger.debug("[SQLValidator] SQL passed all checks. Length=%d chars.", len(sql))
    return True, sql, ""

