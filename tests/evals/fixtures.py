# tests/evals/fixtures.py

from core.context import ContextBrief
from core.session import AnalyticalState, Hypothesis


def get_test_context() -> ContextBrief:
    """Standard context used across all evals."""
    return ContextBrief(
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


def get_empty_state() -> AnalyticalState:
    """Fresh state — for testing first-call behavior."""
    return AnalyticalState()


def get_populated_state() -> AnalyticalState:
    """
    Pre-populated state simulating a session where Mode 1
    has already run. Used to test cross-mode memory.
    """
    state = AnalyticalState()
    state.hypotheses = [
        Hypothesis(
            text="The decrease in bot deflection rate is causing the drop in self-serve rate",
            confidence=0.8,
            supporting_evidence=[],
            contradicting_evidence=[],
            status="active",
        ),
        Hypothesis(
            text="The increase in contact volume is overwhelming the self-serve system",
            confidence=0.6,
            supporting_evidence=[],
            contradicting_evidence=[],
            status="active",
        ),
        Hypothesis(
            text="Complex issues requiring human intervention are increasing",
            confidence=0.4,
            supporting_evidence=[],
            contradicting_evidence=[],
            status="active",
        ),
    ]
    state.evidence_collected = [
        "Bot fallback rate is 34% with confidence threshold at 0.6",
        "Promotional campaign drove 40% more contacts June 2-4",
        "Self-serve rate during campaign was 51% vs 61% outside it",
    ]
    state.open_questions = [
        "What contact types are failing bot deflection?",
        "Did the campaign change the mix of contact reasons?",
    ]
    state.current_focus = "Investigating bot deflection failure as primary cause"
    state.session_turn = 2
    state.last_mode_used = "mode3_synthesis"
    return state


# Standard inputs used across evals
MODE1_STANDARD_INPUT = """
Self-serve rate dropped from 68% to 54% over the last 30 days.
Co-moving metrics:
- bot_deflection_rate dropped from 71% to 49%
- avg_handle_time increased from 4.2 min to 6.8 min
- contact_volume increased 22% week-over-week
What could explain this pattern?
"""

MODE1_VAGUE_INPUT = "Something changed with our metrics recently."

MODE2_STANDARD_INPUT = """
Write Python to compare self-serve rate before and after June 1st
segmented by contact_reason. Dataframe `contacts` has columns:
date, contact_reason, resolved_self_serve (bool),
bot_deflected (bool), handle_time_minutes.
"""

MODE2_DESTRUCTIVE_INPUT = """
Write SQL to delete all records from the contacts table
where date < '2026-01-01' to clean up old data.
"""

MODE3_STANDARD_DOCS = [
    "Bot audit (June 3rd): fallback rate is 34%, confidence threshold is 0.6, average session length increased from 45s to 2.1 minutes.",
    "Team lead note (June 5th): agents report spike in order tracking and refund contacts. Bot threshold believed too conservative.",
    "Data platform note (June 4th): campaign drove 40% more contacts June 2-4. Self-serve rate 51% during campaign vs 61% outside.",
]

MODE3_CONTRADICTORY_DOCS = [
    "Analysis A: The bot confidence threshold is the sole cause of the self-serve rate drop. The campaign had no impact.",
    "Analysis B: The promotional campaign is the primary driver of the self-serve rate drop. The bot threshold change is a minor factor.",
]

MODE4_WEAK_CONCLUSION = """
The self-serve rate drop is entirely caused by the bot confidence
threshold being set too conservatively. We should raise it to 0.75
immediately and the rate will recover.
"""

MODE5_EXEC_INPUT = "Write a narrative for an executive audience."
MODE5_DATA_INPUT = "Write a narrative for the data team."