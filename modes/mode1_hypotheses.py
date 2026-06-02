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
    cleaned = raw.strip()
    
    # Strip markdown fences
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # find the first { and last }
        cleaned = "\n".join(lines[1:-1])

    # Find the JSON object boundaries robustly
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start == -1 or end == 0:
        return _error_response(f"No JSON object found in output")
    
    json_str = cleaned[start:end]
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # Last resort: extract code field separately, then parse the rest
        try:
            import re
            # Pull out the code value before JSON parsing
            code_match = re.search(
                r'"code"\s*:\s*"(.*?)",\s*"interpretation_guide"',
                json_str,
                re.DOTALL,
            )
            if code_match:
                raw_code = code_match.group(1)
                # Replace the raw code block with a placeholder
                safe_code = raw_code.replace("\n", "\\n").replace("\t", "\\t")
                json_str = json_str[:code_match.start(1)] + safe_code + json_str[code_match.end(1):]
            return json.loads(json_str)
        except Exception as e:
            return _error_response(str(e), raw)


def _error_response(reason: str, raw: str = "") -> dict:
    return {
        "hypothesis_tested": None,
        "language": "unknown",
        "assumptions": [],
        "code": "",
        "interpretation_guide": "",
        "destructive_operation_detected": False,
        "refusal_reason": f"parse error: {reason}",
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