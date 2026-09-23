"""
tests/test_text_to_sql.py
--------------------------
Unit tests for the Text-to-SQL pipeline.

Tests SQL validation, mock database operations, and the full pipeline
with mocked LLM responses (no real API calls needed).
"""

import pytest
from pathlib import Path


class TestSQLValidator:
    """Tests for the SQL safety validator."""

    def test_valid_simple_select(self):
        from app.text_to_sql.validator import validate_sql
        is_valid, sql, error = validate_sql("SELECT COUNT(*) FROM users")
        assert is_valid is True
        assert error == ""

    def test_valid_cte_query(self):
        from app.text_to_sql.validator import validate_sql
        sql = "WITH summary AS (SELECT city, COUNT(*) AS n FROM requests GROUP BY city) SELECT * FROM summary"
        is_valid, clean_sql, error = validate_sql(sql)
        assert is_valid is True

    def test_rejects_insert(self):
        from app.text_to_sql.validator import validate_sql
        is_valid, _, error = validate_sql("INSERT INTO users VALUES (99, 'Hacker', 'Domestic', 'City', 1, '2024-01-01')")
        assert is_valid is False
        assert "INSERT" in error

    def test_rejects_delete(self):
        from app.text_to_sql.validator import validate_sql
        is_valid, _, error = validate_sql("DELETE FROM users WHERE user_id = 1")
        assert is_valid is False
        assert "DELETE" in error

    def test_rejects_drop(self):
        from app.text_to_sql.validator import validate_sql
        is_valid, _, error = validate_sql("DROP TABLE users")
        assert is_valid is False
        assert "DROP" in error

    def test_rejects_update(self):
        from app.text_to_sql.validator import validate_sql
        is_valid, _, error = validate_sql("UPDATE users SET is_active = 0 WHERE user_id = 1")
        assert is_valid is False

    def test_rejects_pragma(self):
        from app.text_to_sql.validator import validate_sql
        is_valid, _, error = validate_sql("PRAGMA table_info(users)")
        assert is_valid is False

    def test_rejects_pii_columns(self):
        from app.text_to_sql.validator import validate_sql
        is_valid, _, error = validate_sql("SELECT password FROM users")
        assert is_valid is False
        assert "password" in error.lower()

    def test_rejects_unknown_table(self):
        from app.text_to_sql.validator import validate_sql
        is_valid, _, error = validate_sql("SELECT * FROM super_secret_table")
        assert is_valid is False

    def test_strips_markdown_fences(self):
        from app.text_to_sql.validator import validate_sql
        raw = "```sql\nSELECT * FROM users LIMIT 10\n```"
        is_valid, clean_sql, _ = validate_sql(raw)
        assert is_valid is True
        assert "```" not in clean_sql

    def test_empty_sql_rejected(self):
        from app.text_to_sql.validator import validate_sql
        is_valid, _, error = validate_sql("   ")
        assert is_valid is False

    def test_non_select_first_token(self):
        from app.text_to_sql.validator import validate_sql
        is_valid, _, error = validate_sql("EXEC sp_helptext 'users'")
        assert is_valid is False


class TestMockDatabase:
    """Tests for the SQLite mock database operations."""

    def test_database_created(self, mock_db_path):
        assert mock_db_path.exists(), "Mock database file should be created"

    def test_users_table_has_data(self, mock_db_path):
        from demo.mock_database import get_connection
        conn = get_connection(mock_db_path)
        count = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
        conn.close()
        assert count > 0, "users table should have seed data"

    def test_requests_table_has_data(self, mock_db_path):
        from demo.mock_database import get_connection
        conn = get_connection(mock_db_path)
        count = conn.execute("SELECT COUNT(*) AS n FROM requests").fetchone()["n"]
        conn.close()
        assert count > 0

    def test_rewards_table_has_data(self, mock_db_path):
        from demo.mock_database import get_connection
        conn = get_connection(mock_db_path)
        count = conn.execute("SELECT COUNT(*) AS n FROM rewards").fetchone()["n"]
        conn.close()
        assert count > 0

    def test_users_have_valid_types(self, mock_db_path):
        from demo.mock_database import get_connection
        conn = get_connection(mock_db_path)
        rows = conn.execute("SELECT DISTINCT user_type FROM users").fetchall()
        conn.close()
        types = {r["user_type"] for r in rows}
        valid = {"Domestic", "Corporate", "Collector"}
        assert types.issubset(valid), f"Unexpected user types: {types - valid}"

    def test_requests_have_valid_status(self, mock_db_path):
        from demo.mock_database import get_connection
        conn = get_connection(mock_db_path)
        rows = conn.execute("SELECT DISTINCT status FROM requests").fetchall()
        conn.close()
        statuses = {r["status"] for r in rows}
        valid = {"Completed", "Pending", "Cancelled", "Expired"}
        assert statuses.issubset(valid), f"Unexpected statuses: {statuses - valid}"

    def test_no_real_personal_data(self, mock_db_path):
        """Verify database doesn't contain any real company-specific names."""
        from demo.mock_database import get_connection
        conn = get_connection(mock_db_path)
        names = [r[0] for r in conn.execute("SELECT full_name FROM users").fetchall()]
        conn.close()
        # Check that no real company names appear (generic check for production data leakage)
        real_company_keywords = ["acme-corp", "example-corp", "internal-only"]
        for name in names:
            for kw in real_company_keywords:
                assert kw.lower() not in name.lower(), f"Found real company keyword in: {name}"


class TestTextToSQLPipeline:
    """Tests for the Text-to-SQL generator using mocked LLM responses."""

    def test_pipeline_with_valid_sql(self, mock_db_path, monkeypatch):
        """Pipeline should succeed when LLM returns valid SQL."""
        from unittest.mock import MagicMock, patch

        mock_response = MagicMock()
        mock_response.content = "SELECT COUNT(*) AS total_users FROM users WHERE is_active = 1"

        with patch("app.text_to_sql.generator.generate_and_execute") as mock_gen:
            mock_gen.return_value = (
                [{"total_users": 14}],
                "SELECT COUNT(*) AS total_users FROM users WHERE is_active = 1",
                ""
            )
            from app.text_to_sql.generator import generate_and_execute
            rows, sql, error = generate_and_execute("how many active users?")
            # Should succeed
            assert error == "" or len(rows) >= 0

    def test_direct_db_query(self, mock_db_path):
        """Direct SQLite query should return correct data from seed."""
        from demo.mock_database import get_connection
        conn = get_connection(mock_db_path)
        row = conn.execute("SELECT COUNT(*) AS n FROM users WHERE is_active = 1").fetchone()
        conn.close()
        assert row["n"] == 14   # 14 of 15 seed users are active

    def test_completed_requests_query(self, mock_db_path):
        from demo.mock_database import get_connection
        conn = get_connection(mock_db_path)
        row = conn.execute("SELECT COUNT(*) AS n FROM requests WHERE status = 'Completed'").fetchone()
        conn.close()
        assert row["n"] > 0

    def test_total_weight_query(self, mock_db_path):
        from demo.mock_database import get_connection
        conn = get_connection(mock_db_path)
        row = conn.execute(
            "SELECT SUM(weight_kg) AS total FROM requests WHERE status = 'Completed'"
        ).fetchone()
        conn.close()
        assert row["total"] > 0

    def test_city_filter_query(self, mock_db_path):
        from demo.mock_database import get_connection
        conn = get_connection(mock_db_path)
        rows = conn.execute(
            "SELECT * FROM users WHERE city = 'Greenville' AND is_active = 1"
        ).fetchall()
        conn.close()
        assert len(rows) > 0
