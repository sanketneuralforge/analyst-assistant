# modes/mode1_hypotheses.py

import json
from pathlib import Path
from core.context import ContextBrief
from core.session import AnalyticalState, Hypothesis
from core.llm import call_llm
from rag.retriever import retrieve_domain_context
from guardrails.input_guard import validate_mode1_input
from guardrails.degradation import llm_fallback_response
from core.token_budget import trim_analytical_state

PROMPT_VERSION = "mode1_v1"


def load_prompt() -> str:
    return Path("prompts/mode1_v1.txt").read_text()


def generate_hypotheses(
    user_input: str,
    context: ContextBrief,
    state: AnalyticalState,
    tracer=None,
) -> dict:
    validation = validate_mode1_input(user_input)
    if not validation.is_valid:
        return {
            "_validation_error": validation.error,
            "contradiction_flag": None,
            "hypotheses": [],
            "open_questions": [],
            "current_focus_update": "validation failed",
        }

    retrieval_query = f"{context.primary_metric} {context.domain} {user_input[:200]}"
    domain_context = retrieve_domain_context(retrieval_query)

    system_prompt = f"""
{load_prompt()}

---
{context.to_prompt_block()}

---
{trim_analytical_state(state)}
"""
    augmented_input = user_input
    if domain_context:
        augmented_input = f"{domain_context}\n\n---\n\nANALYST QUESTION:\n{user_input}"

    span = tracer.start_span(
        "mode1_hypotheses",
        model="llama-3.3-70b-versatile",
        metadata={"session_turn": state.session_turn},
    ) if tracer else None

    try:
        raw_output = call_llm(
            system_prompt=system_prompt,
            user_message=augmented_input,
            mode="mode1_hypotheses",
            prompt_version=PROMPT_VERSION,
        )
        if span:
            span.estimate_tokens(augmented_input, raw_output)
            tracer.finish_span(span, status="success")

    except Exception as e:
        if span:
            tracer.finish_span(span, status="error", error=str(e))
        return llm_fallback_response("mode1_hypotheses", str(e))

    result = _parse_json(raw_output)
    _update_state(state, result, user_input, raw_output)

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
        "contradiction_flag": None,
        "hypotheses": [],
        "open_questions": [f"parse error: {reason}"],
        "current_focus_update": "parse error",
        "_raw": raw,
    }


def _update_state(
    state: AnalyticalState,
    result: dict,
    user_input: str,
    raw_output: str,
):
    existing_texts = {h.text for h in state.hypotheses}
    for h in result.get("hypotheses", []):
        if h["text"] not in existing_texts:
            state.hypotheses.append(Hypothesis(
                text=h["text"],
                confidence=h.get("confidence", 0.5),
                supporting_evidence=h.get("supporting_evidence", []),
                contradicting_evidence=h.get("contradicting_evidence", []),
            ))
    state.open_questions.extend(result.get("open_questions", []))
    if focus := result.get("current_focus_update"):
        state.current_focus = focus
    state.add_event(
        mode="mode1_hypotheses",
        user_input=user_input,
        agent_output=raw_output,
    )