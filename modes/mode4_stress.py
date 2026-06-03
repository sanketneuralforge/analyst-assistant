# modes/mode4_stress.py

import json
from pathlib import Path
from core.context import ContextBrief
from core.session import AnalyticalState
from core.llm import call_llm
from guardrails.input_guard import validate_mode4_input
from guardrails.degradation import llm_fallback_response, check_session_health
from core.token_budget import trim_analytical_state

PROMPT_VERSION = "mode4_v1"


def load_prompt() -> str:
    return Path("prompts/mode4_v1.txt").read_text()


def stress_test_conclusion(
    conclusion: str,
    context: ContextBrief,
    state: AnalyticalState,
    tracer=None,
) -> dict:
    validation = validate_mode4_input(conclusion)
    if not validation.is_valid:
        return {
            "_validation_error": validation.error,
            "hypotheses_referenced": [],
            "flaws": [],
            "ignored_ruled_out_hypotheses": None,
            "verdict": "INVALID INPUT",
            "verdict_reason": validation.error,
            "strengthening_analysis": "",
        }

    health = check_session_health(state)

    system_prompt = f"""
{load_prompt()}

---
{context.to_prompt_block()}

---
{trim_analytical_state(state)}
"""

    span = tracer.start_span(
        "mode4_stress_test",
        model="llama-3.3-70b-versatile",
        metadata={
            "hypotheses_count": len(state.hypotheses),
            "session_turn": state.session_turn,
        },
    ) if tracer else None

    try:
        raw_output = call_llm(
            system_prompt=system_prompt,
            user_message=f"Stress-test this conclusion: {conclusion}",
            mode="mode4_stress_test",
            prompt_version=PROMPT_VERSION,
        )
        if span:
            span.estimate_tokens(conclusion, raw_output)
            tracer.finish_span(span, status="success")

    except Exception as e:
        if span:
            tracer.finish_span(span, status="error", error=str(e))
        return llm_fallback_response("mode4_stress_test", str(e))

    result = _parse_json(raw_output)
    state.conclusions_stated.append(conclusion)
    state.add_event(
        mode="mode4_stress_test",
        user_input=conclusion,
        agent_output=raw_output,
    )

    if validation.warning:
        result["_warning"] = validation.warning
    if not health["is_healthy"]:
        result["_session_warnings"] = health["warnings"]

    return result


def _parse_json(raw: str) -> dict:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1])
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start == -1 or end == 0:
        return _error_response("No JSON found")
    try:
        return json.loads(cleaned[start:end])
    except json.JSONDecodeError as e:
        return _error_response(str(e), raw)


def _error_response(reason: str, raw: str = "") -> dict:
    return {
        "hypotheses_referenced": [],
        "flaws": [],
        "ignored_ruled_out_hypotheses": None,
        "verdict": "PARSE ERROR",
        "verdict_reason": str(reason),
        "strengthening_analysis": "retry with clearer conclusion statement",
    }