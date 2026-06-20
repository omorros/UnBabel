"""Local SQLite memory of struggled items. Drives the "needs review" list. No server, no network.

This is the bulletproof critical path (PRD 5). Cognee layers on top later for graph insight;
the demo never depends on Cognee being configured. Schema is one table:
  item(type, language, value, miss_count, seen_count, last_seen)
"""
import os
import sqlite3
import time

from . import config


def _conn():
    os.makedirs(config.DATA_DIR, exist_ok=True)
    c = sqlite3.connect(config.MEMORY_DB)
    c.row_factory = sqlite3.Row
    return c


def init():
    with _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS item(
                id INTEGER PRIMARY KEY,
                type TEXT NOT NULL,            -- 'word' | 'sign'
                language TEXT NOT NULL,
                value TEXT NOT NULL,
                miss_count INTEGER NOT NULL DEFAULT 0,
                seen_count INTEGER NOT NULL DEFAULT 0,
                last_seen REAL NOT NULL,
                UNIQUE(type, language, value)
            )"""
        )


def log_miss(type_, language, value):
    now = time.time()
    with _conn() as c:
        c.execute(
            """INSERT INTO item(type, language, value, miss_count, seen_count, last_seen)
               VALUES(?, ?, ?, 1, 1, ?)
               ON CONFLICT(type, language, value) DO UPDATE SET
                 miss_count = miss_count + 1, seen_count = seen_count + 1, last_seen = ?""",
            (type_, language, value, now, now),
        )


def log_seen(type_, language, value):
    now = time.time()
    with _conn() as c:
        c.execute(
            """INSERT INTO item(type, language, value, miss_count, seen_count, last_seen)
               VALUES(?, ?, ?, 0, 1, ?)
               ON CONFLICT(type, language, value) DO UPDATE SET
                 seen_count = seen_count + 1, last_seen = ?""",
            (type_, language, value, now, now),
        )


def needs_review(limit=10):
    """Highest miss_count, oldest last_seen first. The adaptive review list."""
    with _conn() as c:
        rows = c.execute(
            """SELECT type, language, value, miss_count, seen_count, last_seen
               FROM item WHERE miss_count > 0
               ORDER BY miss_count DESC, last_seen ASC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def stats():
    with _conn() as c:
        words = c.execute("SELECT COUNT(*) FROM item WHERE type='word'").fetchone()[0]
        signs = c.execute("SELECT COUNT(*) FROM item WHERE type='sign'").fetchone()[0]
        return {"words": words, "signs": signs}
