"""
demo/mock_database.py
---------------------
Creates and seeds a local SQLite database with entirely fictional data.
Used exclusively by the Text-to-SQL demo pipeline.

Tables:
    users       — registered platform users (requestors & collectors)
    requests    — pickup/service requests
    rewards     — reward points ledger

Run directly to (re)create the database:
    python -m demo.mock_database
"""

import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent / "demo_data.db"


SCHEMA_SQL = """
-- Users table: platform users (requestors and collectors)
CREATE TABLE IF NOT EXISTS users (
    user_id       INTEGER PRIMARY KEY,
    full_name     TEXT    NOT NULL,
    user_type     TEXT    NOT NULL CHECK(user_type IN ('Domestic','Corporate','Collector')),
    city          TEXT    NOT NULL,
    is_active     INTEGER NOT NULL DEFAULT 1,
    registered_at TEXT    NOT NULL   -- ISO-8601 date
);

-- Requests table: service/pickup requests
CREATE TABLE IF NOT EXISTS requests (
    request_id    INTEGER PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(user_id),
    city          TEXT    NOT NULL,
    status        TEXT    NOT NULL CHECK(status IN ('Completed','Pending','Cancelled','Expired')),
    category      TEXT    NOT NULL,   -- e.g. Aluminium, Plastic, Paper
    weight_kg     REAL    NOT NULL DEFAULT 0,
    scheduled_at  TEXT    NOT NULL,   -- ISO-8601 datetime
    completed_at  TEXT                -- NULL if not completed
);

-- Rewards table: reward points ledger
CREATE TABLE IF NOT EXISTS rewards (
    reward_id     INTEGER PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(user_id),
    points_earned INTEGER NOT NULL DEFAULT 0,
    points_redeemed INTEGER NOT NULL DEFAULT 0,
    reward_type   TEXT    NOT NULL,   -- signup_bonus, business, referral, promotion
    created_at    TEXT    NOT NULL
);
"""

# Entirely fictional seed data — no real individuals or companies
SEED_USERS = [
    (1,  "Alice Morgan",      "Domestic",  "Greenville",  1, "2024-01-15"),
    (2,  "Bob Chen",          "Corporate", "Greenville",  1, "2024-02-01"),
    (3,  "Carlos Rivera",     "Domestic",  "Maplewood",   1, "2024-03-10"),
    (4,  "Diana Patel",       "Corporate", "Greenville",  1, "2024-04-05"),
    (5,  "Edward Kim",        "Collector", "Greenville",  1, "2024-01-20"),
    (6,  "Fatima Al-Hassan",  "Collector", "Maplewood",   1, "2024-02-14"),
    (7,  "George Obi",        "Domestic",  "Lakeside",    1, "2024-05-01"),
    (8,  "Hana Yamamoto",     "Corporate", "Lakeside",    1, "2024-06-15"),
    (9,  "Ivan Petrov",       "Domestic",  "Maplewood",   1, "2024-07-20"),
    (10, "Julia Santos",      "Collector", "Lakeside",    1, "2024-08-01"),
    (11, "Khaled Ibrahim",    "Domestic",  "Greenville",  0, "2024-09-10"),
    (12, "Leila Nguyen",      "Corporate", "Maplewood",   1, "2024-10-05"),
    (13, "Marco Ferrari",     "Domestic",  "Greenville",  1, "2024-11-20"),
    (14, "Nadia Kowalski",    "Collector", "Greenville",  1, "2024-12-01"),
    (15, "Omar Farooq",       "Domestic",  "Lakeside",    1, "2025-01-12"),
]

SEED_REQUESTS = [
    # (request_id, user_id, city, status, category, weight_kg, scheduled_at, completed_at)
    (1,  1,  "Greenville", "Completed", "Aluminium", 12.5, "2025-01-10 09:00", "2025-01-10 11:30"),
    (2,  1,  "Greenville", "Completed", "Plastic",   8.0,  "2025-02-05 10:00", "2025-02-05 12:00"),
    (3,  2,  "Greenville", "Completed", "Paper",     25.0, "2025-01-15 08:00", "2025-01-15 10:45"),
    (4,  2,  "Greenville", "Cancelled", "Steel",     5.0,  "2025-03-01 09:00", None),
    (5,  3,  "Maplewood",  "Completed", "Plastic",   15.0, "2025-02-20 11:00", "2025-02-20 13:15"),
    (6,  3,  "Maplewood",  "Pending",   "Aluminium", 10.0, "2025-04-01 09:00", None),
    (7,  4,  "Greenville", "Completed", "Copper",    6.5,  "2025-01-25 14:00", "2025-01-25 16:00"),
    (8,  4,  "Greenville", "Completed", "Paper",     30.0, "2025-03-10 08:00", "2025-03-10 10:30"),
    (9,  7,  "Lakeside",   "Completed", "Steel",     20.0, "2025-02-28 09:00", "2025-02-28 11:30"),
    (10, 7,  "Lakeside",   "Expired",   "Plastic",   7.5,  "2025-03-15 10:00", None),
    (11, 8,  "Lakeside",   "Completed", "Aluminium", 18.0, "2025-04-05 08:00", "2025-04-05 10:00"),
    (12, 9,  "Maplewood",  "Completed", "Paper",     12.0, "2025-04-10 09:00", "2025-04-10 11:00"),
    (13, 11, "Greenville", "Cancelled", "Steel",     4.0,  "2025-02-10 09:00", None),
    (14, 12, "Maplewood",  "Completed", "Copper",    9.5,  "2025-03-25 10:00", "2025-03-25 12:30"),
    (15, 13, "Greenville", "Pending",   "Plastic",   11.0, "2025-05-01 09:00", None),
    (16, 15, "Lakeside",   "Completed", "Aluminium", 14.5, "2025-04-20 08:00", "2025-04-20 10:15"),
    (17, 1,  "Greenville", "Completed", "Steel",     3.0,  "2025-05-05 09:00", "2025-05-05 11:00"),
    (18, 2,  "Greenville", "Completed", "Plastic",   22.0, "2025-05-12 10:00", "2025-05-12 12:45"),
    (19, 4,  "Greenville", "Pending",   "Aluminium", 8.0,  "2025-06-01 09:00", None),
    (20, 8,  "Lakeside",   "Completed", "Paper",     16.0, "2025-05-20 08:00", "2025-05-20 10:30"),
]

SEED_REWARDS = [
    # (reward_id, user_id, points_earned, points_redeemed, reward_type, created_at)
    (1,  1,  100, 0,   "signup_bonus",  "2024-01-15"),
    (2,  1,  250, 100, "business",      "2025-01-10"),
    (3,  1,  160, 0,   "business",      "2025-02-05"),
    (4,  2,  100, 50,  "signup_bonus",  "2024-02-01"),
    (5,  2,  500, 200, "business",      "2025-01-15"),
    (6,  2,  600, 0,   "business",      "2025-05-12"),
    (7,  3,  100, 0,   "signup_bonus",  "2024-03-10"),
    (8,  3,  300, 150, "business",      "2025-02-20"),
    (9,  4,  100, 100, "signup_bonus",  "2024-04-05"),
    (10, 4,  130, 0,   "business",      "2025-01-25"),
    (11, 4,  50,  0,   "referral",      "2025-02-01"),
    (12, 7,  100, 0,   "signup_bonus",  "2024-05-01"),
    (13, 7,  400, 200, "business",      "2025-02-28"),
    (14, 8,  100, 50,  "signup_bonus",  "2024-06-15"),
    (15, 8,  360, 100, "business",      "2025-04-05"),
    (16, 9,  100, 0,   "signup_bonus",  "2024-07-20"),
    (17, 9,  240, 0,   "business",      "2025-04-10"),
    (18, 12, 100, 0,   "signup_bonus",  "2024-10-05"),
    (19, 12, 190, 50,  "business",      "2025-03-25"),
    (20, 15, 100, 0,   "signup_bonus",  "2025-01-12"),
    (21, 15, 290, 0,   "business",      "2025-04-20"),
    (22, 13, 100, 0,   "signup_bonus",  "2024-11-20"),
    (23, 2,  75,  0,   "promotion",     "2025-03-01"),
    (24, 4,  75,  0,   "promotion",     "2025-03-01"),
]


def create_database(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Create the SQLite database schema and insert seed data."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.executescript(SCHEMA_SQL)

    cur.execute("DELETE FROM rewards")
    cur.execute("DELETE FROM requests")
    cur.execute("DELETE FROM users")

    cur.executemany(
        "INSERT INTO users VALUES (?,?,?,?,?,?)", SEED_USERS
    )
    cur.executemany(
        "INSERT INTO requests VALUES (?,?,?,?,?,?,?,?)", SEED_REQUESTS
    )
    cur.executemany(
        "INSERT INTO rewards VALUES (?,?,?,?,?,?)", SEED_REWARDS
    )

    conn.commit()
    print(f"[MockDB] Database created at: {db_path}")
    print(f"[MockDB]  → {len(SEED_USERS)} users")
    print(f"[MockDB]  → {len(SEED_REQUESTS)} requests")
    print(f"[MockDB]  → {len(SEED_REWARDS)} reward records")
    return conn


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Return a connection to the demo SQLite database (create if missing)."""
    if not db_path.exists():
        return create_database(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


if __name__ == "__main__":
    create_database()

