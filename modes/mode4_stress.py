# modes/mode4_stress.py

import json
from pathlib import Path
from core.context import ContextBrief
from core.session import AnalyticalState
from core.llm import call_llm


def load_prompt() -> str:
    return Path("prompts/mode4_v1.txt").read_text()


def stress_test_conclusion(
    conclusion: str,
    context: ContextBrief,
    state: AnalyticalState,
) -> dict:
    """
    Mode 4: Adversarially stress-test a stated conclusion.
    This mode is the proof of thought partner value — it references
    the session's own hypotheses against the analyst's conclusion.
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
        user_message=f"Stress-test this conclusion: {conclusion}",
    )

    result = _parse_json(raw_output)

    # Log to thread — Mode 4 doesn't add hypotheses but records conclusions
    state.conclusions_stated.append(conclusion)
    state.add_event(
        mode="mode4_stress_test",
        user_input=conclusion,
        agent_output=raw_output,
    )

    return result


def _parse_json(raw: str) -> dict:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1])
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        return {
            "hypotheses_referenced": [],
            "flaws": [],
            "ignored_ruled_out_hypotheses": None,
            "verdict": "PARSE ERROR",
            "verdict_reason": str(e),
            "strengthening_analysis": "retry with clearer conclusion statement",
            "_raw": raw,
        }