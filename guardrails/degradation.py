# guardrails/degradation.py

"""
Graceful degradation handlers.

When something fails — LLM down, ChromaDB empty, parse error —
the system should degrade gracefully rather than crash or
return empty results silently.

Each handler returns a safe fallback response in the same
format as a successful call, so the UI never needs to handle
two different response shapes.
"""

from core.session import AnalyticalState


def llm_fallback_response(mode: str, error: str) -> dict:
    """
    When the LLM call fails completely (not a parse error —
    a genuine API failure after all retries), return a
    structured fallback that the UI can render meaningfully.
    """
    base = {
        "_degraded": True,
        "_error": error,
        "_mode": mode,
    }

    if mode == "mode1_hypotheses":
        return {
            **base,
            "contradiction_flag": None,
            "hypotheses": [],
            "open_questions": [
                "LLM call failed — please retry in a moment.",
                f"Error: {error[:100]}",
            ],
            "current_focus_update": "LLM unavailable — retry required",
        }

    if mode == "mode2_code":
        return {
            **base,
            "hypothesis_tested": None,
            "language": "unknown",
            "assumptions": [],
            "code": "",
            "interpretation_guide": "",
            "destructive_operation_detected": False,
            "refusal_reason": f"LLM unavailable: {error[:100]}",
        }

    if mode == "mode3_synthesis":
        return {
            **base,
            "source_count": 0,
            "facts": [],
            "inferences": [],
            "gaps": ["LLM call failed — synthesis unavailable"],
            "conflicts": [],
            "synthesis_summary": f"Synthesis failed: {error[:100]}",
            "state_contradictions": None,
        }

    if mode == "mode4_stress_test":
        return {
            **base,
            "hypotheses_referenced": [],
            "flaws": [],
            "ignored_ruled_out_hypotheses": None,
            "verdict": "UNAVAILABLE",
            "verdict_reason": f"LLM call failed: {error[:100]}",
            "strengthening_analysis": "Retry when LLM is available.",
        }

    if mode == "mode5_narrative":
        return {
            **base,
            "audience": "unknown",
            "narrative": f"Narrative generation failed: {error[:100]}. Please retry.",
            "flags": [],
            "what_we_know": "LLM unavailable",
            "what_we_dont_know": "Could not generate narrative",
            "recommended_next_step": "Retry when LLM is available",
        }

    return base


def rag_empty_fallback() -> str:
    """
    When ChromaDB has no relevant chunks — return empty string.
    The mode should proceed without RAG context rather than failing.
    This is already handled in retriever.py but made explicit here.
    """
    return ""


def check_session_health(state: AnalyticalState) -> dict:
    """
    Quick health check on the analytical state.
    Returns a dict of warnings about session quality.
    Called before Mode 4 and Mode 5 to warn analyst
    if they are operating without enough session context.
    """
    warnings = []

    if state.session_turn == 0:
        warnings.append(
            "No modes have been run yet this session. "
            "Results will be based only on the ContextBrief."
        )

    if len(state.hypotheses) == 0 and state.session_turn > 0:
        warnings.append(
            "No hypotheses tracked yet. "
            "Run Mode 1 first for better Mode 4 results."
        )

    if len(state.evidence_collected) == 0 and state.session_turn > 1:
        warnings.append(
            "No evidence collected yet. "
            "Run Mode 3 with relevant documents to strengthen the analysis."
        )

    return {
        "is_healthy": len(warnings) == 0,
        "warnings": warnings,
    }