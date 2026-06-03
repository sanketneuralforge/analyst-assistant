# modes/mode5_narrative.py

import json
from pathlib import Path
from core.context import ContextBrief
from core.session import AnalyticalState
from core.llm import call_llm
from guardrails.input_guard import validate_mode5_input
from guardrails.degradation import llm_fallback_response, check_session_health
from core.token_budget import trim_analytical_state

PROMPT_VERSION = "mode5_v1"


def load_prompt() -> str:
    return Path(f"prompts/{PROMPT_VERSION}.txt").read_text()


def draft_narrative(
    user_input: str,
    context: ContextBrief,
    state: AnalyticalState,
    tracer=None,
) -> dict:
    validation = validate_mode5_input(user_input)
    if not validation.is_valid:
        return {
            "_validation_error": validation.error,
            "audience": context.audience,
            "narrative": validation.error,
            "flags": [],
            "what_we_know": "",
            "what_we_dont_know": "",
            "recommended_next_step": "",
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
        "mode5_narrative",
        model="llama-3.1-8b-instant",
        metadata={
            "audience": context.audience,
            "session_turn": state.session_turn,
        },
    ) if tracer else None

    try:
        raw_output = call_llm(
            system_prompt=system_prompt,
            user_message=user_input,
            mode="mode5_narrative",
            prompt_version=PROMPT_VERSION,
        )
        if span:
            span.estimate_tokens(user_input, raw_output)
            tracer.finish_span(span, status="success")

    except Exception as e:
        if span:
            tracer.finish_span(span, status="error", error=str(e))
        return llm_fallback_response("mode5_narrative", str(e))

    result = _parse_json(raw_output)
    state.add_event(
        mode="mode5_narrative",
        user_input=user_input,
        agent_output=raw_output,
    )

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
        "audience": "unknown",
        "narrative": "",
        "flags": [],
        "what_we_know": "",
        "what_we_dont_know": "",
        "recommended_next_step": "",
        "_error": f"parse error: {reason}",
    }