"""
SQLite persistence layer for customer reviews.
Stores reviews.db alongside app.py inside flask_app/.
"""
import sqlite3
import os
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reviews.db")
print(f"[DB] reviews.db -> {DB_PATH}", flush=True)


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------
def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
def init_db() -> None:
    """Create the reviews table if it does not exist (idempotent)."""
    conn = _get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reviews (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL,
            rating     INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
            tags       TEXT    NOT NULL DEFAULT '',
            message    TEXT    NOT NULL,
            created_at TEXT    NOT NULL,
            approved   INTEGER NOT NULL DEFAULT 1
        )
        """
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------
def create_review(name: str, rating: int, tags: list, message: str) -> int:
    """Insert a review and return its new id."""
    conn = _get_db()
    created_at = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "INSERT INTO reviews (name, rating, tags, message, created_at) VALUES (?, ?, ?, ?, ?)",
        (name, rating, ",".join(tags), message, created_at),
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------
def get_reviews(
    limit: int = 6,
    offset: int = 0,
    sort: str = "newest",
    tag: str = None,
) -> tuple:
    """
    Return (list_of_review_dicts, total_count).

    tag filtering uses the comma-wrapped LIKE trick to avoid partial matches:
      stored: "Haircut,Staff"
      query:  ',' || tags || ',' LIKE '%,Staff,%'
    """
    conn = _get_db()

    where = "approved = 1"
    params: list = []

    if tag:
        where += " AND (',' || tags || ',' LIKE ?)"
        params.append(f"%,{tag},%")

    order = "rating DESC, created_at DESC" if sort == "highest" else "created_at DESC"

    total: int = conn.execute(
        f"SELECT COUNT(*) FROM reviews WHERE {where}", params
    ).fetchone()[0]

    rows = conn.execute(
        f"SELECT * FROM reviews WHERE {where} ORDER BY {order} LIMIT ? OFFSET ?",
        params + [limit, offset],
    ).fetchall()

    conn.close()
    return [dict(r) for r in rows], total
