# core/token_budget.py

"""
Token budget management for AnalyticalState injection.

The AnalyticalState grows with every mode call. If injected in full
every time, by turn 20 you're sending 8,000+ tokens of state context
on every call — burning quota and risking context window limits.

Strategy:
- Count tokens before every LLM call
- If over budget, trim the state intelligently
- Always keep: hypotheses + conclusions (highest value)
- Trim first: old thread events + duplicate open questions
"""

from core.session import AnalyticalState


# ── Token limits ─────────────────────────────────────────────────
# Groq llama-3.3-70b context window: 128k tokens
# We budget conservatively to leave room for prompts + output
MAX_STATE_TOKENS = 3000   # max tokens for AnalyticalState block
MAX_CONTEXT_TOKENS = 1500  # max tokens for ContextBrief block
MAX_TOTAL_INJECTION = 5000  # hard ceiling for all injected context

# Rough token estimator — 1 token ≈ 4 characters for English text
def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def trim_analytical_state(state: AnalyticalState) -> str:
    """
    Produce a token-budget-aware version of the AnalyticalState
    prompt block. Trims aggressively if needed, never loses
    hypotheses or conclusions.
    
    Returns the formatted string ready for prompt injection.
    """
    full_block = state.to_prompt_block()
    token_count = estimate_tokens(full_block)

    # Under budget — inject in full
    if token_count <= MAX_STATE_TOKENS:
        return full_block

    # Over budget — build trimmed version
    # Priority order: hypotheses > conclusions > evidence > questions > thread
    sections = []

    # Always include: hypotheses (most valuable for cross-mode memory)
    hypotheses_text = "\n".join([
        f"  - [{h.status.upper()}] {h.text} ({h.confidence:.0%})"
        for h in state.hypotheses
    ]) or "  None yet."
    sections.append(f"## ANALYTICAL STATE (trimmed — token budget)\n"
                   f"Current Focus: {state.current_focus}\n"
                   f"Session Turn: {state.session_turn}\n\n"
                   f"Hypotheses Tracked:\n{hypotheses_text}")

    # Always include: conclusions stated
    if state.conclusions_stated:
        conclusions = "\n".join([f"  - {c[:100]}" for c in state.conclusions_stated[-3:]])
        sections.append(f"Conclusions Stated (last 3):\n{conclusions}")

    current = "\n\n".join(sections)

    # Add evidence if budget allows
    if estimate_tokens(current) + 300 < MAX_STATE_TOKENS:
        evidence = "\n".join([f"  - {e[:80]}" for e in state.evidence_collected[-5:]])
        if evidence:
            current += f"\n\nEvidence (last 5):\n{evidence}"

    # Add open questions if budget allows
    if estimate_tokens(current) + 200 < MAX_STATE_TOKENS:
        questions = "\n".join([f"  - {q[:80]}" for q in state.open_questions[-3:]])
        if questions:
            current += f"\n\nOpen Questions (last 3):\n{questions}"

    # Add thread if budget allows — last 2 turns only
    if estimate_tokens(current) + 300 < MAX_STATE_TOKENS and state.thread:
        recent = state.thread[-2:]
        thread_text = "\n".join([
            f"  Turn {e.turn} ({e.mode}): {e.user_input[:60]}..."
            for e in recent
        ])
        current += f"\n\nRecent Thread (last 2 turns):\n{thread_text}"

    return current


def get_session_token_summary(state: AnalyticalState) -> dict:
    """
    Returns a summary of token usage for the current session.
    Used by the UI to show token health in the sidebar.
    """
    full_state = state.to_prompt_block()
    trimmed_state = trim_analytical_state(state)

    return {
        "full_state_tokens": estimate_tokens(full_state),
        "trimmed_state_tokens": estimate_tokens(trimmed_state),
        "is_trimmed": estimate_tokens(full_state) > MAX_STATE_TOKENS,
        "budget_used_pct": min(100, int(estimate_tokens(full_state) / MAX_STATE_TOKENS * 100)),
        "hypotheses_count": len(state.hypotheses),
        "evidence_count": len(state.evidence_collected),
        "turns": state.session_turn,
    }