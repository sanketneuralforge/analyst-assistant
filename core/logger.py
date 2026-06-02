# core/logger.py

import sqlite3
import time
from datetime import datetime
from pathlib import Path

DB_PATH = Path("db/call_history.db")


def init_db():
    """
    Create the call history table if it doesn't exist.
    Call once at session start.
    """
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS call_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT NOT NULL,
            mode        TEXT NOT NULL,
            prompt_version TEXT NOT NULL,
            user_input  TEXT NOT NULL,
            full_output TEXT NOT NULL,
            latency_ms  INTEGER NOT NULL,
            model       TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def log_call(
    mode: str,
    prompt_version: str,
    user_input: str,
    full_output: str,
    latency_ms: int,
    model: str = "llama-3.3-70b-versatile",
):
    """
    Log one LLM call to SQLite.
    Called after every mode execution — never before.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT INTO call_history
            (timestamp, mode, prompt_version, user_input, full_output, latency_ms, model)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now().isoformat(),
            mode,
            prompt_version,
            user_input,
            full_output,
            latency_ms,
            model,
        ),
    )
    conn.commit()
    conn.close()


def get_history(limit: int = 20) -> list[dict]:
    """Fetch recent call history for display in UI."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM call_history ORDER BY timestamp DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]