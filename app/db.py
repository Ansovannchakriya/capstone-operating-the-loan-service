"""SQLite storage. Small on purpose: one file, no server to run.
Borrowers are seeded at start-up because the Module 2 spec has no endpoint to create them."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from app import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS borrowers (
    id INTEGER PRIMARY KEY,
    province TEXT NOT NULL,
    monthly_income REAL NOT NULL,
    credit_score INTEGER NOT NULL,
    years_employed INTEGER NOT NULL,
    has_default INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    borrower_id INTEGER NOT NULL REFERENCES borrowers(id),
    amount_usd INTEGER NOT NULL,
    term_months INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    submitted_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER NOT NULL REFERENCES applications(id),
    default_probability REAL NOT NULL,
    model_version TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""

# id, province, monthly income USD, credit score, years employed, has defaulted before
SEED_BORROWERS = [
    (1042, "Siem Reap", 3000, 780, 10, 0),    # strong profile
    (1043, "Phnom Penh", 400, 420, 1, 1),     # weak profile (used by the verify "golden" check)
    (1044, "Battambang", 1500, 650, 5, 0),    # average profile
    (1045, "Kampot", 2200, 720, 8, 0),
]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@contextmanager
def connect():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    Path(config.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript(SCHEMA)
        conn.executemany("INSERT OR IGNORE INTO borrowers VALUES (?, ?, ?, ?, ?, ?)", SEED_BORROWERS)
