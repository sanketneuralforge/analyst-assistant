# main.py

import json
from core.context import ContextBrief
from core.session import AnalyticalState
from core.logger import init_db
from core.proactive import get_proactive_suggestions
from modes.mode1_hypotheses import generate_hypotheses
from modes.mode2_code import draft_code
from modes.mode3_synthesis import synthesise_docs
from modes.mode4_stress import stress_test_conclusion
from modes.mode5_narrative import draft_narrative


def print_section(title: str, data: dict):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")
    print(json.dumps(data, indent=2))


def print_suggestions(suggestions: list[dict]):
    if not suggestions:
        return
    print(f"\n💡 THOUGHT PARTNER NUDGES:")
    for s in suggestions:
        priority_icon = "🔴" if s['priority'] == 'high' else "🟡" if s['priority'] == 'medium' else "🟢"
        print(f"  {priority_icon} {s['action']}")
        print(f"     → {s['reason']}")


def main():
    # Initialize SQLite call history
    init_db()

    # ── 1. Brief the agent ───────────────────────────────────────
    context = ContextBrief(
        company_name="Deliveroo Care",
        domain="customer support operations",
        primary_metric="self-serve rate",
        metric_definition="percentage of customer contacts resolved without a human agent",
        time_period="last 30 days (May 2026)",
        audience="data team",
        stakes="weekly ops review with Head of Care",
        known_context="a new bot deflection flow was launched on June 1st 2026",
        constraints="do not reference competitor benchmarks",
    )

    state = AnalyticalState()

    print("\n" + "="*60)
    print("  ANALYST ASSISTANT — THOUGHT PARTNER MODE")
    print("="*60)

    # ── 2. Mode 1: Hypotheses ────────────────────────────────────
    print("\n[MODE 1] Generating hypotheses...")
    mode1_result = generate_hypotheses(
        user_input="""
        Self-serve rate dropped from 68% to 54% over the last 30 days.
        Co-moving metrics:
        - bot_deflection_rate dropped from 71% to 49%
        - avg_handle_time increased from 4.2 min to 6.8 min
        - contact_volume increased 22% week-over-week
        What could explain this pattern?
        """,
        context=context,
        state=state,
    )
    print_section("MODE 1 — Hypotheses", mode1_result)
    print_suggestions(get_proactive_suggestions(state))

    # ── 3. Mode 3: Synthesise docs ───────────────────────────────
    print("\n[MODE 3] Synthesising documents...")
    mode3_result = synthesise_docs(
        documents=[
            "Bot audit report (June 3rd): The new deflection flow has a 34% fallback rate — contacts the bot cannot handle are routed to agents. The fallback trigger is 'low confidence score below 0.6'. Average bot session length increased from 45s to 2.1 minutes.",
            "Support team lead note (June 5th): Agents report a spike in contacts about order tracking and refunds. These were previously handled by the bot. Team lead believes the bot confidence threshold was set too conservatively after the June 1st launch.",
            "Data platform note (June 4th): contact_volume spike appears driven by a promotional campaign that ran June 2-4. The campaign drove 40% more contacts than forecast. Self-serve rate during the campaign window was 51% vs 61% outside it.",
        ],
        context=context,
        state=state,
    )
    print_section("MODE 3 — Synthesis", mode3_result)
    print_suggestions(get_proactive_suggestions(state))

    # ── 4. Mode 2: Draft code ────────────────────────────────────
    print("\n[MODE 2] Drafting investigation code...")
    mode2_result = draft_code(
        user_input="""
        Write Python code to compare self-serve rate and bot deflection rate 
        before and after June 1st, segmented by contact reason. 
        I have a dataframe called `contacts` with columns:
        date, contact_reason, resolved_self_serve (bool), 
        bot_deflected (bool), handle_time_minutes.
        """,
        context=context,
        state=state,
    )
    print_section("MODE 2 — Code Draft", mode2_result)
    print_suggestions(get_proactive_suggestions(state))

    # ── 5. Mode 4: Stress test ───────────────────────────────────
    print("\n[MODE 4] Stress-testing conclusion...")
    mode4_result = stress_test_conclusion(
        conclusion="The self-serve rate drop is primarily caused by the bot confidence threshold being set too conservatively, not by the volume spike from the campaign.",
        context=context,
        state=state,
    )
    print_section("MODE 4 — Stress Test", mode4_result)
    print_suggestions(get_proactive_suggestions(state))

    # ── 6. Mode 5: Narrative ─────────────────────────────────────
    print("\n[MODE 5] Drafting narrative...")
    mode5_result = draft_narrative(
        user_input="Write a narrative for the data team summarising this investigation.",
        context=context,
        state=state,
    )
    print_section("MODE 5 — Narrative", mode5_result)

    # ── 7. Final state summary ───────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  SESSION SUMMARY")
    print(f"{'='*60}")
    print(f"  Total turns: {state.session_turn}")
    print(f"  Hypotheses tracked: {len(state.hypotheses)}")
    print(f"  Evidence collected: {len(state.evidence_collected)}")
    print(f"  Conclusions stated: {len(state.conclusions_stated)}")
    print(f"  Open questions: {len(state.open_questions)}")
    print(f"  Call history logged to: db/call_history.db")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()