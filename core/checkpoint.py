# core/checkpoint.py

"""
Session checkpointing — persist AnalyticalState to SQLite
after every mode call so sessions survive server restarts.

The checkpoint stores the full session as JSON. On resume,
the state is reconstructed from the stored JSON.

This solves the biggest production limitation: losing all
investigation progress when the Streamlit server restarts.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from dataclasses import asdict

from core.session import AnalyticalState, Hypothesis, SessionEvent

DB_PATH = Path("db/checkpoints.db")


def init_checkpoint_db():
    """Create the checkpoints table if it doesn't exist."""
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS session_checkpoints (
            session_id   TEXT PRIMARY KEY,
            updated_at   TEXT NOT NULL,
            turn         INTEGER NOT NULL,
            state_json   TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_checkpoint(session_id: str, state: AnalyticalState):
    """
    Persist the current AnalyticalState to SQLite.
    Called after every mode execution.
    Uses session_id as the key — same session overwrites.
    """
    # Serialize state to JSON
    state_data = {
        "hypotheses": [
            {
                "text": h.text,
                "confidence": h.confidence,
                "supporting_evidence": h.supporting_evidence,
                "contradicting_evidence": h.contradicting_evidence,
                "status": h.status,
            }
            for h in state.hypotheses
        ],
        "evidence_collected": state.evidence_collected,
        "conclusions_stated": state.conclusions_stated,
        "open_questions": state.open_questions,
        "investigated_paths": state.investigated_paths,
        "current_focus": state.current_focus,
        "session_turn": state.session_turn,
        "last_mode_used": state.last_mode_used,
        "thread": [
            {
                "turn": e.turn,
                "mode": e.mode,
                "user_input": e.user_input,
                "agent_output": e.agent_output,
                "timestamp": e.timestamp,
            }
            for e in state.thread
        ],
    }

    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT OR REPLACE INTO session_checkpoints
            (session_id, updated_at, turn, state_json)
        VALUES (?, ?, ?, ?)
    """, (
        session_id,
        datetime.now().isoformat(),
        state.session_turn,
        json.dumps(state_data),
    ))
    conn.commit()
    conn.close()


def load_checkpoint(session_id: str) -> AnalyticalState | None:
    """
    Reconstruct an AnalyticalState from a stored checkpoint.
    Returns None if no checkpoint exists for this session_id.
    """
    init_checkpoint_db()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT state_json FROM session_checkpoints WHERE session_id = ?",
        (session_id,)
    ).fetchone()
    conn.close()

    if not row:
        return None

    data = json.loads(row["state_json"])
    state = AnalyticalState()

    state.hypotheses = [
        Hypothesis(
            text=h["text"],
            confidence=h["confidence"],
            supporting_evidence=h["supporting_evidence"],
            contradicting_evidence=h["contradicting_evidence"],
            status=h["status"],
        )
        for h in data.get("hypotheses", [])
    ]
    state.evidence_collected = data.get("evidence_collected", [])
    state.conclusions_stated = data.get("conclusions_stated", [])
    state.open_questions = data.get("open_questions", [])
    state.investigated_paths = data.get("investigated_paths", [])
    state.current_focus = data.get("current_focus", "not yet determined")
    state.session_turn = data.get("session_turn", 0)
    state.last_mode_used = data.get("last_mode_used", "none")
    state.thread = [
        SessionEvent(
            turn=e["turn"],
            mode=e["mode"],
            user_input=e["user_input"],
            agent_output=e["agent_output"],
            timestamp=e["timestamp"],
        )
        for e in data.get("thread", [])
    ]

    return state


def list_checkpoints() -> list[dict]:
    """List all saved sessions for the resume UI."""
    init_checkpoint_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT session_id, updated_at, turn FROM session_checkpoints ORDER BY updated_at DESC LIMIT 20"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_checkpoint(session_id: str):
    """Delete a checkpoint — called on session reset."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "DELETE FROM session_checkpoints WHERE session_id = ?",
        (session_id,)
    )
    conn.commit()
    conn.close()