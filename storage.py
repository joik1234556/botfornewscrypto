"""SQLite-backed storage for tracking which articles have already been posted."""

import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path("posted_articles.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS posted_articles (
            url TEXT PRIMARY KEY,
            title TEXT,
            posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    return conn


def is_posted(url: str) -> bool:
    """Return True if the article URL has already been posted."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM posted_articles WHERE url = ?", (url,)
        ).fetchone()
        return row is not None


def mark_posted(url: str, title: str = "") -> None:
    """Record that the article with *url* has been posted."""
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO posted_articles (url, title) VALUES (?, ?)",
            (url, title),
        )
        conn.commit()
    logger.debug("Marked as posted: %s", url)


def get_posted_count() -> int:
    """Return total number of posted articles."""
    with _connect() as conn:
        row = conn.execute("SELECT COUNT(*) FROM posted_articles").fetchone()
        return row[0] if row else 0
