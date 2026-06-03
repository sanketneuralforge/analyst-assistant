# api/session_store.py

from dataclasses import asdict
from core.session import AnalyticalState
from core.context import ContextBrief


class SessionStore:
    """
    In-memory session registry keyed by session_id.

    Each slot holds a live AnalyticalState object and a ContextBrief.
    For multi-process / multi-replica production, replace the internal
    dict with a Redis client and add serialize/deserialize helpers.
    """

    def __init__(self):
        self._sessions: dict[str, dict] = {}

    # ── Lifecycle ────────────────────────────────────────────────

    def create(self, session_id: str) -> None:
        self._sessions[session_id] = {
            "state": AnalyticalState(),
            "brief": None,
        }

    def exists(self, session_id: str) -> bool:
        return session_id in self._sessions

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def count(self) -> int:
        return len(self._sessions)

    # ── State ────────────────────────────────────────────────────

    def get_state(self, session_id: str) -> AnalyticalState | None:
        s = self._sessions.get(session_id)
        return s["state"] if s else None

    def replace_state(self, session_id: str, state: AnalyticalState) -> None:
        if session_id in self._sessions:
            self._sessions[session_id]["state"] = state

    # ── Brief ────────────────────────────────────────────────────

    def get_brief(self, session_id: str) -> ContextBrief | None:
        s = self._sessions.get(session_id)
        return s["brief"] if s else None

    def set_brief(self, session_id: str, brief: ContextBrief) -> None:
        if session_id in self._sessions:
            self._sessions[session_id]["brief"] = brief

    # ── Serialization ────────────────────────────────────────────

    @staticmethod
    def serialize_state(state: AnalyticalState) -> dict:
        """Convert AnalyticalState to a JSON-safe dict for API responses."""
        return asdict(state)


store = SessionStore()
