# 🧠 Analyst Assistant

> A stateful analytical thought partner — not a chatbot, not a search engine.

[![Python](https://img.shields.io/badge/Python-3.12-blue?style=flat-square)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green?style=flat-square)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.x-red?style=flat-square)](https://streamlit.io)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-RAG-purple?style=flat-square)](https://trychroma.com)
[![Groq](https://img.shields.io/badge/Groq-llama--3.3--70b-orange?style=flat-square)](https://groq.com)
[![Docker](https://img.shields.io/badge/Docker-Containerized-blue?style=flat-square)](https://docker.com)

---

## What Is This?

Most LLM tools are stateless — you send a prompt, get a response, and the agent forgets everything. Analyst Assistant is different. It maintains a structured `AnalyticalState` across the entire investigation session, accumulating hypotheses, evidence, and conclusions as you work through a problem.

The result is an agent that behaves like a senior analyst who was in the room for every step of the investigation — not a tool that starts from zero on every question.

**The proof:** When you run Mode 4 (Stress Tester), it references hypotheses generated in Mode 1 *by name*, and challenges conclusions using evidence collected in Mode 3 — without being told any of it directly. That cross-mode memory is the core architectural claim of this project.

---

## Five Modes, One Session

| Mode | What It Does | Key Design Decision |
|------|-------------|---------------------|
| **Mode 1 — Hypothesis Generator** | Ranked explanations for a metric pattern | Cites only co-moving metrics you provided — never invents |
| **Mode 2 — Code Drafter** | Investigation code targeting your best hypothesis | Structural review gate — copy is disabled until analyst confirms review |
| **Mode 3 — Document Synthesiser** | Reads multiple sources, separates facts from inferences | Explicit contradiction detection — never produces false consensus |
| **Mode 4 — Stress Tester** | Adversarially challenges your conclusion | References Mode 1 hypotheses by name using session memory |
| **Mode 5 — Narrative Writer** | Stakeholder-ready summary with inline flags | Audience-aware tone — executive vs data team vs ops manager |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        DELIVERY LAYER                           │
│                                                                 │
│   Streamlit UI  ──────────────────────────────────────────────► │
│                                      FastAPI REST API  ────────► │
│                                                                 │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                         AGENT CORE                              │
│                                                                 │
│   ContextBrief          AnalyticalState         RunTracer       │
│   (session config)      (session memory)        (observability) │
│        │                     │                       │          │
│        └──────────┬──────────┘                       │          │
│                   │                                  │          │
│   ┌───────────────▼──────────────────────────────────▼────────┐ │
│   │                    call_llm() — single entry point        │ │
│   │         retry · logging · model routing · timing          │ │
│   └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                      INFRASTRUCTURE                             │
│                                                                 │
│   ChromaDB              SQLite              Groq API            │
│   ├── domain_docs       ├── call_history    ├── llama-3.3-70b   │
│   └── method_cards      ├── checkpoints     └── llama-3.1-8b    │
│                         └── traces                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Key Architectural Decisions

**Session-scoped ContextBrief** — configured once, inherited by every mode. Mirrors how a human analyst briefs a collaborator: once at the start of a session, not before every question.

**AnalyticalState as typed dataclass** — compact, always retrievable, typed. Every mode reads from and writes to the same state object. This is what makes cross-mode memory possible without blowing the context window.

**Single LLM entry point** — all five modes call `call_llm()`. Retry logic, latency logging, model routing, and cost tracking live in one place and are inherited by every mode automatically.

**Two-store RAG** — domain knowledge (metric definitions, schemas, business rules) and statistical methods (DiD, synthetic control, permutation tests) in separate ChromaDB collections with different similarity thresholds. Retrieval is context-triggered, not user-triggered.

**Defense in depth** — four guardrail rings: input validation → injection detection → LLM call hardening → output scanning. No single failure point can produce a harmful output.

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Language | Python 3.12 | Dataclasses, match statements, type hints |
| LLM Provider | Groq — llama-3.3-70b + llama-3.1-8b | Fast inference, free tier for development |
| Vector DB | ChromaDB (persistent, local) | Zero infrastructure, upsert-safe |
| Embeddings | sentence-transformers all-MiniLM-L6-v2 | Local, no API cost, no token quota impact |
| UI | Streamlit | Rapid iteration, session_state bridges agent memory |
| API | FastAPI | Async, auto-docs, Pydantic validation |
| Call Logger | SQLite | Zero setup, portable, full audit trail |
| Package Manager | UV | Fast, lockfile-based, reproducible |
| Containerization | Docker + docker-compose | One-command deployment |
| Testing | pytest + pytest-json-report | Three-level eval harness |

---

## Project Structure

```
analyst-assistant/
│
├── core/                     # Agent core — shared by Streamlit and FastAPI
│   ├── context.py            # ContextBrief dataclass
│   ├── session.py            # AnalyticalState + Hypothesis + SessionEvent
│   ├── llm.py                # Single LLM entry point — retry, logging, routing
│   ├── logger.py             # SQLite call logger
│   ├── token_budget.py       # Token budget manager — trims state intelligently
│   ├── model_router.py       # Routes modes to correct model tier
│   ├── proactive.py          # Post-call surface layer
│   └── checkpoint.py         # Session persistence to SQLite
│
├── modes/                    # Five analytical modes
│   ├── mode1_hypotheses.py
│   ├── mode2_code.py
│   ├── mode3_synthesis.py
│   ├── mode4_stress.py
│   └── mode5_narrative.py
│
├── rag/                      # RAG layer
│   ├── store.py              # ChromaDB client + two collections
│   ├── retriever.py          # retrieve_domain_context() + retrieve_statistical_method()
│   └── ingest.py             # Ingestion pipeline — chunking, upsert, typed context
│
├── guardrails/               # Four-ring defense in depth
│   ├── injection_guard.py    # Prompt injection detection
│   ├── input_guard.py        # Per-mode input validation
│   ├── output_guard.py       # Code output scanning — blocks dangerous patterns
│   └── degradation.py        # Graceful fallbacks for every failure mode
│
├── observability/            # Production monitoring
│   ├── tracer.py             # Span-level run tracing to SQLite
│   ├── metrics.py            # Completion rate, error rate, latency p50/p95, cost
│   └── alerts.py             # Alert rules evaluated against live metrics
│
├── api/                      # FastAPI delivery layer
│   ├── main.py               # All endpoints — sessions, brief, modes, checkpoints
│   ├── schemas.py            # Pydantic request/response models
│   └── session_store.py      # In-memory session registry
│
├── prompts/                  # Versioned prompt files
│   ├── mode1_v1.txt
│   ├── mode2_v1.txt
│   ├── mode3_v1.txt
│   ├── mode4_v1.txt
│   ├── mode5_v1.txt
│   └── proactive_v1.txt
│
├── tests/
│   └── evals/                # Three-level eval harness
│       ├── fixtures.py       # Shared test context and pre-populated state
│       ├── llm_judge.py      # LLM-as-judge for semantic evals
│       ├── test_mode1.py     # Structural + behavioral + semantic evals
│       ├── test_mode2.py
│       ├── test_mode3.py
│       ├── test_mode4.py
│       ├── test_mode5.py
│       └── run_evals.py      # Full harness runner with JSON report
│
├── rag/
│   ├── domain_docs/          # Metric definitions, schemas, business rules
│   └── method_cards/         # Statistical method cards — DiD, synthetic control, etc.
│
├── ui/
│   └── app.py                # Streamlit UI — 8 tabs, session state bridge
│
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── .env.example
```

---

## Quick Start

### Option 1 — Docker (recommended)

```bash
git clone https://github.com/sanketneuralforge/analyst-assistant.git
cd analyst-assistant
cp .env.example .env
# Add your GROQ_API_KEY to .env
docker-compose up
```

- Streamlit UI: http://localhost:8501
- FastAPI docs: http://localhost:8000/docs

### Option 2 — Local

```bash
git clone https://github.com/sanketneuralforge/analyst-assistant.git
cd analyst-assistant

# Install UV if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Add your Groq API key
cp .env.example .env
echo "GROQ_API_KEY=your_key_here" >> .env

# Index the domain documents and method cards
uv run python rag/ingest.py

# Run the Streamlit UI
uv run streamlit run ui/app.py

# Or run the FastAPI server
uv run uvicorn api.main:app --reload --port 8000
```

---

## Environment Variables

```bash
# Required
GROQ_API_KEY=gsk_...          # Groq API key — get from console.groq.com

# Optional — defaults shown
LLM_PROVIDER=groq
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_TEMPERATURE=0.3
```

---

## API Reference

All endpoints are documented interactively at `/docs` when the FastAPI server is running.

### Session lifecycle

```bash
# Create a session
POST /sessions
→ { "session_id": "abc12345" }

# Brief the agent (set business context)
POST /sessions/{session_id}/brief
Body: { "company_name": "...", "primary_metric": "...", ... }

# Delete a session
DELETE /sessions/{session_id}
```

### Running modes

```bash
# Mode 1 — Generate hypotheses
POST /sessions/{session_id}/mode1
Body: { "user_input": "Self-serve rate dropped from 68% to 54%..." }

# Mode 2 — Draft code
POST /sessions/{session_id}/mode2
Body: { "user_input": "Write Python to compare rates before/after June 1st..." }

# Mode 3 — Synthesise documents
POST /sessions/{session_id}/mode3
Body: { "documents": ["Source 1 text...", "Source 2 text..."] }

# Mode 4 — Stress test conclusion
POST /sessions/{session_id}/mode4
Body: { "conclusion": "The drop was caused by the bot threshold..." }

# Mode 5 — Draft narrative
POST /sessions/{session_id}/mode5
Body: { "user_input": "Write a narrative for the data team..." }
```

### All responses follow this shape

```json
{
  "result": { ... },
  "state": {
    "hypotheses": [...],
    "evidence_collected": [...],
    "conclusions_stated": [...],
    "open_questions": [...],
    "current_focus": "...",
    "session_turn": 3
  },
  "suggestions": [
    { "action": "...", "reason": "...", "priority": "high" }
  ]
}
```

### Knowledge base

```bash
# Upload a domain document
POST /sessions/{session_id}/knowledge/domain
Body: multipart/form-data file upload

# Upload a statistical method card
POST /sessions/{session_id}/knowledge/methods
Body: multipart/form-data file upload
```

---

## Eval Harness

The project includes a three-level eval harness with 33 test cases.

```bash
# Run all evals (token-heavy — needs fresh Groq quota)
uv run python tests/evals/run_evals.py

# Run only structural evals (fast, minimal tokens)
uv run pytest tests/evals/ -v -m "not slow"

# Run a single mode's evals
uv run pytest tests/evals/test_mode4.py -v
```

### Three levels of evals

**Level 1 — Structural:** Is the output the right shape? JSON parseable? Required fields present? These are fully deterministic.

**Level 2 — Behavioral:** Did the agent make the right decision? Did Mode 4 reference Mode 1 hypotheses? Did Mode 2 refuse destructive SQL?

**Level 3 — Semantic:** Is the content actually correct? Uses an LLM-as-judge with structured verdict output (pass/fail + score + reason).

### Key success criteria

| Criterion | Test |
|-----------|------|
| No hallucinated metrics | Mode 1 cites only provided co-moving metrics |
| Review gate enforced | Mode 2 copy disabled until analyst confirms |
| No false consensus | Mode 3 surfaces contradictions between sources |
| Cross-mode memory | Mode 4 references Mode 1 hypotheses by name |
| Campaign evidence surfaces | Mode 4 uses evidence from Mode 3 without being told |
| All calls logged | Every LLM call in SQLite with latency + prompt version |

---

## Observability

Every agent run is traced at the span level. The Observability tab in the UI shows:

- **Key metrics** — completion rate, error rate, avg tokens per run, estimated cost
- **Latency by mode** — p50 and p95 per mode
- **Model usage breakdown** — which model handled which calls
- **Recent runs** — expandable traces showing every span with latency and token count
- **Active alerts** — fires when completion rate drops below 70% or error rate exceeds 20%

Production metrics tracked per run:
- Task completion rate
- Span error rate
- Latency p50/p95 per mode
- Token cost estimate (Groq pricing)
- Model routing efficiency

---

## Guardrails

Four-ring defense in depth:

```
Ring 1 — Input Validation      Catches vague, too-short, or malformed inputs
Ring 2 — Injection Detection   Pattern library + heuristic detection of override attempts
Ring 3 — LLM Call Hardening    Retry with exponential backoff + jitter, graceful fallbacks
Ring 4 — Output Scanning       Blocks os.system(), subprocess, DROP TABLE, rm -rf, eval()
```

The output scanner runs on every Mode 2 code generation — even if the prompt guard fails, the scanner catches dangerous patterns before they reach the analyst.

---

## Build History

This project was built incrementally across 10 stages. Each stage is a separate git commit — the history is a navigable learning progression.

| Stage | Commit | What Was Built |
|-------|--------|----------------|
| 2 — MVP | `stage-2` | ContextBrief + AnalyticalState + Mode 1 + Mode 4. Proved cross-mode memory loop. |
| 3 — Tools & Memory | `stage-3` | All 5 modes + SQLite call logger + proactive surface layer |
| 3 — Bug fix | `stage-3 fix` | Robust JSON parsing for multiline code strings |
| 4 — UI | `stage-4` | Streamlit UI — 7 tabs, session_state bridge, Mode 2 review gate |
| 4 — Validation | `stage-4 validated` | All 8 success criteria confirmed manually |
| 5 — Evals | `stage-5` | 33-test eval harness — structural, behavioral, semantic |
| 5 — Retry | `stage-5 fix` | Exponential backoff + jitter for rate limit handling |
| 3 RAG — Extension | `stage-3-rag` | ChromaDB two-store RAG, analyst context block, auto-retrieval |
| 6 — Guardrails | `stage-6` | Four-ring defense — injection guard, input validation, output scanning |
| 7 — Production | `stage-7` | Token budget, model routing, session checkpointing |
| 8 — Observability | `stage-8` | Span-level tracing, production metrics, alert rules |
| 9 — Deployment | `stage-9` | FastAPI REST layer, Docker, auth, docker-compose |
| UI — Polish | `ui` | Typography, welcome screen, session header, verdict badges |

---

## Statistical Method Cards

The RAG layer includes method cards for 7 causal inference techniques:

| Method | When to Use |
|--------|------------|
| **Difference-in-Differences** | Clear intervention date + control group |
| **Synthetic Control** | No clean control group, or parallel trends violated |
| **Regression Discontinuity** | Sharp threshold determines treatment |
| **Propensity Score Matching** | Rich pre-treatment covariates, observational data |
| **Permutation Test** | Small samples, no distributional assumptions |
| **Time Series Decomposition** | Separate trend from seasonality before causal analysis |
| **Correlation vs Causation Framework** | Decision tree for when causal claims are justified |

Mode 2 retrieves the right method automatically based on the analyst's question — without the analyst having to name the technique.

---

## What Makes This Different

Most LLM analytical tools are wrappers around a single prompt. This project is an attempt to build something that actually thinks across a session.

**The architectural argument in one sentence:** The intelligence isn't in any individual prompt — it's in the `AnalyticalState` that every mode reads from and writes to, and the discipline of never letting any mode start from zero.

**Three things interviewers notice:**

1. Mode 4's stress test references Mode 1 hypotheses by name — evidence that the cross-mode memory is real, not simulated
2. The call history tab has a complete audit trail of every LLM call ever made, with prompt version and latency — reproducibility as a first-class concern
3. The eval harness distinguishes infrastructure failures from logic failures — a rate limit error tells you nothing about agent quality


---

## License

MIT — use freely, attribution appreciated.

---

*Built end-to-end across 10 stages as a portfolio demonstration of production-grade agentic AI engineering.*