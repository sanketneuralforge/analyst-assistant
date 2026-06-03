# core/model_router.py

"""
Model routing — match the right model to the right task.

Not every call needs the most capable model. Routing saves
tokens, reduces latency, and makes the system more cost-efficient.

Current providers:
- Groq llama-3.3-70b-versatile: high capability, slower, more tokens
- Groq llama-3.1-8b-instant: fast, cheap, good for simple tasks

Routing logic:
- Analytical reasoning (Mode 1, 4): needs 70b
- Code generation (Mode 2): needs 70b
- Document synthesis (Mode 3): needs 70b  
- Narrative writing (Mode 5): 8b is enough for structured output
- Proactive nudges: 8b is enough
- LLM judge: 8b is enough for binary evaluation
- Input classification: 8b is enough
"""

from config.settings import settings


# ── Model definitions ─────────────────────────────────────────────
MODELS = {
    "primary": "llama-3.3-70b-versatile",    # full capability
    "fast": "llama-3.1-8b-instant",           # fast + cheap
}

# ── Routing table ─────────────────────────────────────────────────
# Maps mode name to model tier
ROUTING_TABLE = {
    "mode1_hypotheses": "primary",    # causal reasoning needs full model
    "mode2_code": "primary",          # code generation needs full model
    "mode3_synthesis": "primary",     # contradiction detection needs full model
    "mode4_stress_test": "primary",   # adversarial reasoning needs full model
    "mode5_narrative": "fast",        # structured narrative — 8b handles well
    "proactive": "fast",              # suggestions — 8b handles well
    "llm_judge": "fast",              # binary eval — 8b handles well
    "unknown": "primary",             # default to primary if mode unknown
}

# ── Temperature table ─────────────────────────────────────────────
TEMPERATURE_TABLE = {
    "mode1_hypotheses": 0.3,
    "mode2_code": 0.2,        # lower for code — want determinism
    "mode3_synthesis": 0.3,
    "mode4_stress_test": 0.3,
    "mode5_narrative": 0.4,   # slightly higher for narrative variety
    "proactive": 0.4,
    "llm_judge": 0.1,         # near-deterministic for evaluation
    "unknown": 0.3,
}


def get_model_for_mode(mode: str) -> str:
    """Return the model string for a given mode."""
    tier = ROUTING_TABLE.get(mode, "primary")
    return MODELS[tier]


def get_temperature_for_mode(mode: str) -> float:
    """Return the appropriate temperature for a given mode."""
    return TEMPERATURE_TABLE.get(mode, settings.groq_temperature)


def get_routing_summary() -> dict:
    """
    Returns the full routing table for display in the UI.
    Useful for debugging and explaining cost decisions.
    """
    return {
        mode: {
            "model": MODELS[ROUTING_TABLE[mode]],
            "temperature": TEMPERATURE_TABLE[mode],
            "tier": ROUTING_TABLE[mode],
        }
        for mode in ROUTING_TABLE
    }