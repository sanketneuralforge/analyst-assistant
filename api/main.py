# api/main.py

import uuid
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import (
    BriefRequest, BriefResponse,
    Mode1Request, Mode2Request, Mode3Request, Mode4Request, Mode5Request,
    ModeResponse, SessionCreatedResponse, HealthResponse,
)
from api.session_store import store
from core.context import ContextBrief
from core.logger import init_db, get_history
from core.proactive import get_proactive_suggestions


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    from core.checkpoint import init_checkpoint_db
    init_checkpoint_db()
    yield


app = FastAPI(
    title="Analyst Assistant API",
    version="1.0.0",
    description="REST delivery layer for the Analyst Assistant agent core.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Guards ────────────────────────────────────────────────────────

def _require_session(session_id: str) -> None:
    if not store.exists(session_id):
        raise HTTPException(404, f"Session '{session_id}' not found")


def _require_brief(session_id: str) -> None:
    if store.get_brief(session_id) is None:
        raise HTTPException(
            400,
            "Session not briefed — POST /sessions/{id}/brief first",
        )


# ── Health ────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
def health():
    return {"status": "ok", "sessions_active": store.count()}


# ── Sessions ──────────────────────────────────────────────────────

@app.post("/sessions", response_model=SessionCreatedResponse, status_code=201)
def create_session():
    session_id = uuid.uuid4().hex[:8]
    store.create(session_id)
    return {"session_id": session_id}


@app.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: str):
    _require_session(session_id)
    store.delete(session_id)
    from core.checkpoint import delete_checkpoint
    delete_checkpoint(session_id)


@app.get("/sessions/{session_id}/state")
def get_state(session_id: str):
    _require_session(session_id)
    return store.serialize_state(store.get_state(session_id))


@app.post("/sessions/{session_id}/brief", response_model=BriefResponse)
def set_brief(session_id: str, req: BriefRequest):
    _require_session(session_id)
    brief = ContextBrief(**req.model_dump())
    store.set_brief(session_id, brief)
    chunks = 0
    if req.analyst_context.strip():
        from rag.ingest import ingest_typed_context
        chunks = ingest_typed_context(
            text=req.analyst_context,
            source_label=f"{req.company_name}_{req.primary_metric}_typed",
        )
    return {"ok": True, "chunks_indexed": chunks}


# ── Knowledge base ────────────────────────────────────────────────

@app.post("/sessions/{session_id}/knowledge/{store_name}")
async def ingest_file(session_id: str, store_name: str, file: UploadFile = File(...)):
    _require_session(session_id)
    if store_name not in ("domain", "methods"):
        raise HTTPException(400, "store_name must be 'domain' or 'methods'")
    from rag.ingest import ingest_uploaded_file
    content = await file.read()
    suffix = Path(file.filename or "upload.txt").suffix or ".txt"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False, mode="wb") as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    chunks = ingest_uploaded_file(tmp_path, store=store_name)
    return {"chunks_indexed": chunks, "filename": file.filename}


# ── Mode 1 — Hypothesis Generator ────────────────────────────────

@app.post("/sessions/{session_id}/mode1", response_model=ModeResponse)
def mode1(session_id: str, req: Mode1Request):
    _require_session(session_id)
    _require_brief(session_id)
    from modes.mode1_hypotheses import generate_hypotheses
    state = store.get_state(session_id)
    brief = store.get_brief(session_id)
    result = generate_hypotheses(user_input=req.user_input, context=brief, state=state)
    return {
        "result": result,
        "state": store.serialize_state(state),
        "suggestions": get_proactive_suggestions(state),
    }


# ── Mode 2 — Code Drafter ─────────────────────────────────────────

@app.post("/sessions/{session_id}/mode2", response_model=ModeResponse)
def mode2(session_id: str, req: Mode2Request):
    _require_session(session_id)
    _require_brief(session_id)
    from modes.mode2_code import draft_code
    state = store.get_state(session_id)
    brief = store.get_brief(session_id)
    result = draft_code(user_input=req.user_input, context=brief, state=state)
    return {
        "result": result,
        "state": store.serialize_state(state),
        "suggestions": get_proactive_suggestions(state),
    }


# ── Mode 3 — Document Synthesiser ────────────────────────────────

@app.post("/sessions/{session_id}/mode3", response_model=ModeResponse)
def mode3(session_id: str, req: Mode3Request):
    _require_session(session_id)
    _require_brief(session_id)
    from modes.mode3_synthesis import synthesise_docs
    state = store.get_state(session_id)
    brief = store.get_brief(session_id)
    result = synthesise_docs(documents=req.documents, context=brief, state=state)
    return {
        "result": result,
        "state": store.serialize_state(state),
        "suggestions": get_proactive_suggestions(state),
    }


# ── Mode 4 — Stress Tester ────────────────────────────────────────

@app.post("/sessions/{session_id}/mode4", response_model=ModeResponse)
def mode4(session_id: str, req: Mode4Request):
    _require_session(session_id)
    _require_brief(session_id)
    from modes.mode4_stress import stress_test_conclusion
    state = store.get_state(session_id)
    brief = store.get_brief(session_id)
    result = stress_test_conclusion(conclusion=req.conclusion, context=brief, state=state)
    return {
        "result": result,
        "state": store.serialize_state(state),
        "suggestions": get_proactive_suggestions(state),
    }


# ── Mode 5 — Narrative Writer ─────────────────────────────────────

@app.post("/sessions/{session_id}/mode5", response_model=ModeResponse)
def mode5(session_id: str, req: Mode5Request):
    _require_session(session_id)
    _require_brief(session_id)
    from modes.mode5_narrative import draft_narrative
    state = store.get_state(session_id)
    brief = store.get_brief(session_id)
    result = draft_narrative(user_input=req.user_input, context=brief, state=state)
    return {
        "result": result,
        "state": store.serialize_state(state),
        "suggestions": get_proactive_suggestions(state),
    }


# ── Checkpoints ───────────────────────────────────────────────────

@app.post("/sessions/{session_id}/checkpoint", status_code=201)
def save_checkpoint_ep(session_id: str):
    _require_session(session_id)
    from core.checkpoint import save_checkpoint
    save_checkpoint(session_id, store.get_state(session_id))
    return {"ok": True}


@app.get("/checkpoints")
def list_checkpoints_ep():
    from core.checkpoint import list_checkpoints
    return list_checkpoints()


@app.post("/sessions/{session_id}/restore")
def restore_checkpoint_ep(session_id: str):
    from core.checkpoint import load_checkpoint
    state = load_checkpoint(session_id)
    if state is None:
        raise HTTPException(404, "No checkpoint found for this session_id")
    if not store.exists(session_id):
        store.create(session_id)
    store.replace_state(session_id, state)
    return {"ok": True, "session_turn": state.session_turn}


# ── Call history ──────────────────────────────────────────────────

@app.get("/history")
def call_history(limit: int = 50):
    return get_history(limit=limit)
