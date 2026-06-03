# observability/tracer.py

"""
Span-level run tracing.

Every agent run gets a run_id. Every mode call within that run
gets a span. Spans are stored in SQLite and queryable by run_id.

This is what lets you debug a failed run — you pull the full
trace and see exactly what happened at each step.
"""

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

DB_PATH = Path("db/traces.db")


def init_traces_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            run_id       TEXT PRIMARY KEY,
            session_id   TEXT NOT NULL,
            started_at   TEXT NOT NULL,
            ended_at     TEXT,
            status       TEXT DEFAULT 'running',
            total_spans  INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            total_ms     INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS spans (
            span_id      TEXT PRIMARY KEY,
            run_id       TEXT NOT NULL,
            mode         TEXT NOT NULL,
            started_at   TEXT NOT NULL,
            ended_at     TEXT,
            duration_ms  INTEGER,
            model        TEXT,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            status       TEXT DEFAULT 'running',
            error        TEXT,
            metadata     TEXT,
            FOREIGN KEY (run_id) REFERENCES runs(run_id)
        )
    """)
    conn.commit()
    conn.close()


@dataclass
class Span:
    """One mode call within a run."""
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    run_id: str = ""
    mode: str = ""
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    ended_at: str = ""
    duration_ms: int = 0
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    status: str = "running"
    error: str = ""
    metadata: dict = field(default_factory=dict)

    def finish(self, status: str = "success", error: str = ""):
        self.ended_at = datetime.now().isoformat()
        self.status = status
        self.error = error

    def estimate_tokens(self, input_text: str, output_text: str):
        self.input_tokens = max(1, len(input_text) // 4)
        self.output_tokens = max(1, len(output_text) // 4)


@dataclass
class Run:
    """One complete agent session from brief to final mode call."""
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    session_id: str = ""
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    ended_at: str = ""
    status: str = "running"
    spans: list[Span] = field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        return sum(s.input_tokens + s.output_tokens for s in self.spans)

    @property
    def total_ms(self) -> int:
        return sum(s.duration_ms for s in self.spans)

    @property
    def failed_spans(self) -> list[Span]:
        return [s for s in self.spans if s.status == "error"]


class RunTracer:
    """
    Context manager for tracing a complete agent run.
    
    Usage:
        tracer = RunTracer(session_id="abc123")
        with tracer.span("mode1_hypotheses", model="llama-3.3-70b") as span:
            result = generate_hypotheses(...)
            span.estimate_tokens(input_text, result)
    """

    def __init__(self, session_id: str):
        init_traces_db()
        self.run = Run(session_id=session_id)
        self._save_run()

    def _save_run(self):
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            INSERT OR REPLACE INTO runs
                (run_id, session_id, started_at, ended_at, status,
                 total_spans, total_tokens, total_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.run.run_id,
            self.run.session_id,
            self.run.started_at,
            self.run.ended_at or None,
            self.run.status,
            len(self.run.spans),
            self.run.total_tokens,
            self.run.total_ms,
        ))
        conn.commit()
        conn.close()

    def start_span(self, mode: str, model: str = "", metadata: dict = None) -> Span:
        span = Span(
            run_id=self.run.run_id,
            mode=mode,
            model=model,
            metadata=metadata or {},
        )
        self.run.spans.append(span)
        self._save_span(span)
        return span

    def finish_span(self, span: Span, status: str = "success", error: str = ""):
        span.finish(status=status, error=error)
        # Calculate duration
        try:
            start = datetime.fromisoformat(span.started_at)
            end = datetime.fromisoformat(span.ended_at)
            span.duration_ms = int((end - start).total_seconds() * 1000)
        except Exception:
            span.duration_ms = 0
        self._save_span(span)
        self._save_run()

    def _save_span(self, span: Span):
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            INSERT OR REPLACE INTO spans
                (span_id, run_id, mode, started_at, ended_at,
                 duration_ms, model, input_tokens, output_tokens,
                 status, error, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            span.span_id,
            span.run_id,
            span.mode,
            span.started_at,
            span.ended_at or None,
            span.duration_ms,
            span.model,
            span.input_tokens,
            span.output_tokens,
            span.status,
            span.error or None,
            json.dumps(span.metadata),
        ))
        conn.commit()
        conn.close()

    def finish_run(self, status: str = "success"):
        self.run.ended_at = datetime.now().isoformat()
        self.run.status = status
        self._save_run()


def get_recent_runs(limit: int = 20) -> list[dict]:
    """Fetch recent runs for the observability dashboard."""
    init_traces_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT * FROM runs
        ORDER BY started_at DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_spans_for_run(run_id: str) -> list[dict]:
    """Fetch all spans for a specific run."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT * FROM spans
        WHERE run_id = ?
        ORDER BY started_at ASC
    """, (run_id,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]