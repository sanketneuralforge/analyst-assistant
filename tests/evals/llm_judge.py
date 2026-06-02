# tests/evals/llm_judge.py

import json
from core.llm import call_llm

JUDGE_PROMPT = """
You are an eval judge for an AI analytical assistant.
You will be given an output from the assistant and a specific 
property to evaluate. 

Return ONLY valid JSON — no markdown, no preamble:
{
  "pass": true or false,
  "score": 0.0 to 1.0,
  "reason": "one sentence explanation"
}

Be strict. A score of 1.0 means perfect. 0.0 means completely failed.
Pass is true only if score >= 0.7.
"""


def judge(output: str, property_to_evaluate: str) -> dict:
    """
    Ask an LLM to evaluate a semantic property of agent output.
    Returns: {pass: bool, score: float, reason: str}
    """
    user_message = f"""
AGENT OUTPUT:
{output}

PROPERTY TO EVALUATE:
{property_to_evaluate}

Return your verdict as JSON.
"""
    raw = call_llm(
        system_prompt=JUDGE_PROMPT,
        user_message=user_message,
        mode="llm_judge",
        prompt_version="judge_v1",
        temperature=0.1,  # very low — we want consistent judgments
    )

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1])

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"pass": False, "score": 0.0, "reason": f"judge parse error: {raw[:100]}"}