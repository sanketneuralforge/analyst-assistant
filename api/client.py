# api/client.py

import os
from pathlib import Path

import httpx

_DEFAULT_BASE = os.getenv("ANALYST_API_URL", "http://localhost:8000")
_TIMEOUT = httpx.Timeout(120.0, connect=5.0)  # LLM calls can take a while


class AnalystAPIClient:
    """
    Synchronous HTTP client used by the Streamlit UI to talk to FastAPI.

    All methods raise httpx.HTTPStatusError on 4xx/5xx, and
    httpx.ConnectError when the API server is unreachable.
    """

    def __init__(self, base_url: str = _DEFAULT_BASE):
        self.base = base_url.rstrip("/")

    # ── Internal helpers ─────────────────────────────────────────

    def _get(self, path: str, **kwargs) -> dict | list:
        r = httpx.get(f"{self.base}{path}", timeout=_TIMEOUT, **kwargs)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, **kwargs) -> dict:
        r = httpx.post(f"{self.base}{path}", timeout=_TIMEOUT, **kwargs)
        r.raise_for_status()
        return r.json()

    def _delete(self, path: str) -> None:
        r = httpx.delete(f"{self.base}{path}", timeout=_TIMEOUT)
        r.raise_for_status()

    # ── Health ───────────────────────────────────────────────────

    def health(self) -> dict:
        return self._get("/health")

    # ── Sessions ─────────────────────────────────────────────────

    def create_session(self) -> str:
        return self._post("/sessions")["session_id"]

    def delete_session(self, session_id: str) -> None:
        self._delete(f"/sessions/{session_id}")

    def get_state(self, session_id: str) -> dict:
        return self._get(f"/sessions/{session_id}/state")

    def set_brief(self, session_id: str, brief: dict) -> dict:
        return self._post(f"/sessions/{session_id}/brief", json=brief)

    # ── Modes ────────────────────────────────────────────────────

    def mode1(self, session_id: str, user_input: str) -> dict:
        return self._post(
            f"/sessions/{session_id}/mode1",
            json={"user_input": user_input},
        )

    def mode2(self, session_id: str, user_input: str) -> dict:
        return self._post(
            f"/sessions/{session_id}/mode2",
            json={"user_input": user_input},
        )

    def mode3(self, session_id: str, documents: list[str]) -> dict:
        return self._post(
            f"/sessions/{session_id}/mode3",
            json={"documents": documents},
        )

    def mode4(self, session_id: str, conclusion: str) -> dict:
        return self._post(
            f"/sessions/{session_id}/mode4",
            json={"conclusion": conclusion},
        )

    def mode5(self, session_id: str, user_input: str = "") -> dict:
        return self._post(
            f"/sessions/{session_id}/mode5",
            json={"user_input": user_input},
        )

    # ── Knowledge base ───────────────────────────────────────────

    def ingest_file(self, session_id: str, file_path: Path, store_name: str) -> dict:
        with open(file_path, "rb") as f:
            r = httpx.post(
                f"{self.base}/sessions/{session_id}/knowledge/{store_name}",
                files={"file": (file_path.name, f, "text/plain")},
                timeout=_TIMEOUT,
            )
        r.raise_for_status()
        return r.json()

    # ── Checkpoints ──────────────────────────────────────────────

    def save_checkpoint(self, session_id: str) -> dict:
        return self._post(f"/sessions/{session_id}/checkpoint")

    def list_checkpoints(self) -> list:
        return self._get("/checkpoints")

    def restore_checkpoint(self, session_id: str) -> dict:
        return self._post(f"/sessions/{session_id}/restore")

    # ── History ──────────────────────────────────────────────────

    def get_history(self, limit: int = 50) -> list:
        return self._get("/history", params={"limit": limit})
