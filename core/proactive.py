# core/proactive.py

import json
from core.session import AnalyticalState
from core.llm import call_llm

PROMPT_VERSION = "proactive_v1"

PROACTIVE_PROMPT = """
VERSION: proactive_v1

You are an analytical thought partner monitoring a live investigation.
You have just observed the analyst complete a mode call.
Your job: surface 1-3 things the analyst should investigate next
that they have NOT yet considered.

RULES:
1. Read the analytical state carefully. Only suggest things not 
   already in investigated_paths or open_questions.
2. Be specific — name the exact metric, table, or comparison to run.
3. Rank by expected impact on resolving the current focus.
4. Keep each suggestion to one sentence.
5. If the session is turn 1, be conservative — one suggestion only.

OUTPUT FORMAT (return valid JSON only, no markdown, no preamble):
{
  "suggestions": [
    {
      "action": "specific thing to investigate",
      "reason": "why this matters to the current focus",
      "priority": "high | medium | low"
    }
  ]
}
"""


def get_proactive_suggestions(state: AnalyticalState) -> list[dict]:
    """
    Lightweight post-call that reads the analytical state and
    surfaces what the analyst hasn't thought of yet.
    Called automatically after every mode execution.
    """
    raw_output = call_llm(
        system_prompt=PROACTIVE_PROMPT,
        user_message=state.to_prompt_block(),
        mode="proactive",
        prompt_version=PROMPT_VERSION,
        temperature=0.4,   # slightly higher — we want creative suggestions
    )

    cleaned = raw_output.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1])

    try:
        result = json.loads(cleaned)
        return result.get("suggestions", [])
    except json.JSONDecodeError:
        return []