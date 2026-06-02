# modes/mode3_synthesis.py

import json
from pathlib import Path
from core.context import ContextBrief
from core.session import AnalyticalState
from core.llm import call_llm

PROMPT_VERSION = "mode3_v1"


def load_prompt() -> str:
    return Path(f"prompts/{PROMPT_VERSION}.txt").read_text()


def synthesise_docs(
    documents: list[str],
    context: ContextBrief,
    state: AnalyticalState,
) -> dict:
    """
    Mode 3: Synthesise multiple documents, detect contradictions,
    cross-reference against analytical state.
    """
    if len(documents) < 2:
        return {
            "source_count": len(documents),
            "facts": [],
            "inferences": [],
            "gaps": [],
            "conflicts": [],
            "synthesis_summary": "",
            "state_contradictions": None,
            "_error": "Provide at least 2 documents for synthesis.",
        }

    # Format documents as numbered sources
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

    raw_output = call_llm(
        system_prompt=system_prompt,
        user_message=formatted_docs,
        mode="mode3_synthesis",
        prompt_version=PROMPT_VERSION,
    )

    result = _parse_json(raw_output)

    # Add facts to evidence collected
    for fact in result.get("facts", []):
        state.evidence_collected.append(fact)

    # Add gaps to open questions
    for gap in result.get("gaps", []):
        state.open_questions.append(gap)

    state.add_event(
        mode="mode3_synthesis",
        user_input=f"{len(documents)} documents provided",
        agent_output=raw_output,
    )

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