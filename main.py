# main.py

import json
from core.context import ContextBrief
from core.session import AnalyticalState
from modes.mode1_hypotheses import generate_hypotheses
from modes.mode4_stress import stress_test_conclusion


def print_section(title: str, data: dict):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")
    print(json.dumps(data, indent=2))


def main():
    # ── 1. Brief the agent (done once per session) ──────────────
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

    # ── 2. Initialize empty analytical state ────────────────────
    state = AnalyticalState()

    print("\n" + "="*60)
    print("  ANALYST ASSISTANT — THOUGHT PARTNER MODE")
    print("  Session starting...")
    print(f"  Metric: {context.primary_metric}")
    print(f"  Period: {context.time_period}")
    print("="*60)

    # ── 3. Mode 1: Generate hypotheses ──────────────────────────
    print("\n[MODE 1] Generating hypotheses...")

    mode1_input = """
    Self-serve rate dropped from 68% to 54% over the last 30 days.
    Co-moving metrics I can see:
    - bot_deflection_rate dropped from 71% to 49%
    - avg_handle_time increased from 4.2 min to 6.8 min
    - contact_volume increased 22% week-over-week
    What could explain this pattern?
    """

    mode1_result = generate_hypotheses(
        user_input=mode1_input,
        context=context,
        state=state,
    )

    print_section("MODE 1 OUTPUT — Hypotheses", mode1_result)

    # ── 4. Show state after Mode 1 ───────────────────────────────
    print(f"\n[STATE] Hypotheses tracked: {len(state.hypotheses)}")
    print(f"[STATE] Current focus: {state.current_focus}")
    print(f"[STATE] Session turn: {state.session_turn}")

    # ── 5. Mode 4: Stress-test a conclusion ──────────────────────
    print("\n[MODE 4] Stress-testing conclusion...")

    # Analyst has jumped to a conclusion — let's see if the agent pushes back
    analyst_conclusion = """
    The self-serve rate drop is entirely caused by the new bot flow 
    launched on June 1st. We should roll back the bot immediately.
    """

    mode4_result = stress_test_conclusion(
        conclusion=analyst_conclusion,
        context=context,
        state=state,
    )

    print_section("MODE 4 OUTPUT — Stress Test", mode4_result)

    # ── 6. Show final state ──────────────────────────────────────
    print(f"\n[STATE] Conclusions recorded: {state.conclusions_stated}")
    print(f"[STATE] Session turns completed: {state.session_turn}")
    print(f"\n{'='*60}")
    print("  SESSION COMPLETE")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()