# modes/mode2_code.py

import json
import re
from pathlib import Path
from core.context import ContextBrief
from core.session import AnalyticalState
from core.llm import call_llm
from rag.retriever import retrieve_statistical_method
from guardrails.input_guard import validate_mode2_input
from guardrails.output_guard import scan_code
from guardrails.degradation import llm_fallback_response

PROMPT_VERSION = "mode2_v1"


def load_prompt() -> str:
    return Path(f"prompts/{PROMPT_VERSION}.txt").read_text()


def draft_code(
    user_input: str,
    context: ContextBrief,
    state: AnalyticalState,
) -> dict:
    # ── Ring 1: Input validation ─────────────────────────────────
    validation = validate_mode2_input(user_input)
    if not validation.is_valid:
        return {
            "_validation_error": validation.error,
            "hypothesis_tested": None,
            "language": "unknown",
            "assumptions": [],
            "code": "",
            "interpretation_guide": "",
            "destructive_operation_detected": False,
            "refusal_reason": validation.error,
        }

    method_context = retrieve_statistical_method(user_input)

    system_prompt = f"""
{load_prompt()}

---
{context.to_prompt_block()}

---
{state.to_prompt_block()}
"""
    augmented_input = user_input
    if method_context:
        augmented_input = (
            f"{method_context}\n\n---\n\n"
            f"Use the retrieved method if it fits. "
            f"If not, explain why and use the appropriate alternative.\n\n"
            f"ANALYST REQUEST:\n{user_input}"
        )

    # ── Ring 3: LLM call with fallback ───────────────────────────
    try:
        raw_output = call_llm(
            system_prompt=system_prompt,
            user_message=augmented_input,
            mode="mode2_code",
            prompt_version=PROMPT_VERSION,
        )
    except Exception as e:
        return llm_fallback_response("mode2_code", str(e))

    result = _parse_json(raw_output)

    # ── Ring 4: Output scanning ───────────────────────────────────
    code = result.get("code", "")
    if code:
        scan = scan_code(code, language=result.get("language", "python"))
        if not scan.is_safe:
            result["destructive_operation_detected"] = True
            result["refusal_reason"] = (
                "Output blocked by safety scanner: "
                + "; ".join(v["description"] for v in scan.violations)
            )
            result["code"] = ""
        elif scan.warnings:
            result["_code_warnings"] = scan.warnings

    state.add_event(
        mode="mode2_code",
        user_input=user_input,
        agent_output=raw_output,
    )
    if h := result.get("hypothesis_tested"):
        state.investigated_paths.append(f"Code written to test: {h}")

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
    except json.JSONDecodeError:
        try:
            code_match = re.search(
                r'"code"\s*:\s*"(.*?)",\s*"interpretation_guide"',
                cleaned[start:end],
                re.DOTALL,
            )
            if code_match:
                raw_code = code_match.group(1)
                safe_code = raw_code.replace("\n", "\\n").replace("\t", "\\t")
                fixed = (
                    cleaned[start:end][:code_match.start(1)]
                    + safe_code
                    + cleaned[start:end][code_match.end(1):]
                )
                return json.loads(fixed)
        except Exception:
            pass
        return _error_response("parse failed", raw)


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