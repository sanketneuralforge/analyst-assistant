# modes/mode3_synthesis.py

import json
from pathlib import Path
from core.context import ContextBrief
from core.session import AnalyticalState
from core.llm import call_llm
from guardrails.input_guard import validate_mode3_input
from guardrails.degradation import llm_fallback_response

PROMPT_VERSION = "mode3_v1"


def load_prompt() -> str:
    return Path(f"prompts/{PROMPT_VERSION}.txt").read_text()


def synthesise_docs(
    documents: list[str],
    context: ContextBrief,
    state: AnalyticalState,
) -> dict:
    # ── Ring 1: Input validation ─────────────────────────────────
    validation = validate_mode3_input(documents)
    if not validation.is_valid:
        return {
            "_validation_error": validation.error,
            "source_count": len(documents),
            "facts": [],
            "inferences": [],
            "gaps": [],
            "conflicts": [],
            "synthesis_summary": "",
            "state_contradictions": None,
            "_error": validation.error,
        }

    formatted_docs = "\n\n".join([
        f"SOURCE {i+1}:\n{doc}"
        for i, doc in enumerate(documents)
    ])

    system_prompt = f"""
{load_prompt()}

---
{context.to_prompt_block()}

---
{state.to_prompt_block()}
"""

    # ── Ring 3: LLM call with fallback ───────────────────────────
    try:
        raw_output = call_llm(
            system_prompt=system_prompt,
            user_message=formatted_docs,
            mode="mode3_synthesis",
            prompt_version=PROMPT_VERSION,
        )
    except Exception as e:
        return llm_fallback_response("mode3_synthesis", str(e))

    result = _parse_json(raw_output)

    for fact in result.get("facts", []):
        state.evidence_collected.append(fact)
    for gap in result.get("gaps", []):
        state.open_questions.append(gap)

    state.add_event(
        mode="mode3_synthesis",
        user_input=f"{len(documents)} documents provided",
        agent_output=raw_output,
    )

    if validation.warning:
        result["_warning"] = validation.warning

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
        "source_count": 0,
        "facts": [],
        "inferences": [],
        "gaps": [],
        "conflicts": [],
        "synthesis_summary": "",
        "state_contradictions": None,
        "_error": f"parse error: {reason}",
    }