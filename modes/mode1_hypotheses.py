# modes/mode1_hypotheses.py

import json
from pathlib import Path
from core.context import ContextBrief
from core.session import AnalyticalState, Hypothesis
from core.llm import call_llm


def load_prompt() -> str:
    return Path("prompts/mode1_v1.txt").read_text()


def generate_hypotheses(
    user_input: str,
    context: ContextBrief,
    state: AnalyticalState,
) -> dict:
    """
    Mode 1: Generate ranked hypotheses for a pattern or question.
    Updates AnalyticalState in place after the call.
    """
    system_prompt = f"""
{load_prompt()}

---
{context.to_prompt_block()}

---
{state.to_prompt_block()}
"""

    raw_output = call_llm(
        system_prompt=system_prompt,
        user_message=user_input,
    )

    # Parse structured output
    result = _parse_json(raw_output)

    # Update AnalyticalState from the result
    _update_state(state, result, user_input, raw_output)

    return result


def _parse_json(raw: str) -> dict:
    """
    Strip any accidental markdown fences and parse.
    LLMs sometimes wrap JSON in ```json blocks even when told not to.
    """
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1])
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        # Don't crash — return a safe degraded response
        return {
            "contradiction_flag": None,
            "hypotheses": [],
            "open_questions": [f"JSON parse failed: {e}"],
            "current_focus_update": "parse error — retry with clearer input",
            "_raw": raw,
        }


def _update_state(
    state: AnalyticalState,
    result: dict,
    user_input: str,
    raw_output: str,
):
    """Write mode 1 findings back into the shared AnalyticalState."""

    # Add new hypotheses (avoid duplicates)
    existing_texts = {h.text for h in state.hypotheses}
    for h in result.get("hypotheses", []):
        if h["text"] not in existing_texts:
            state.hypotheses.append(Hypothesis(
                text=h["text"],
                confidence=h.get("confidence", 0.5),
                supporting_evidence=h.get("supporting_evidence", []),
                contradicting_evidence=h.get("contradicting_evidence", []),
            ))

    # Add open questions
    state.open_questions.extend(result.get("open_questions", []))

    # Update focus
    if focus := result.get("current_focus_update"):
        state.current_focus = focus

    # Log event to thread
    state.add_event(
        mode="mode1_hypotheses",
        user_input=user_input,
        agent_output=raw_output,
    )