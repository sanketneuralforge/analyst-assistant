# core/session.py

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Hypothesis:
    text: str
    confidence: float              # 0.0 - 1.0
    supporting_evidence: list[str] = field(default_factory=list)
    contradicting_evidence: list[str] = field(default_factory=list)
    status: str = "active"         # "active" | "confirmed" | "ruled_out"


@dataclass
class SessionEvent:
    """One entry in the session timeline."""
    turn: int
    mode: str
    user_input: str
    agent_output: str
    timestamp: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )


@dataclass
class AnalyticalState:
    # What we know
    hypotheses: list[Hypothesis] = field(default_factory=list)
    evidence_collected: list[str] = field(default_factory=list)
    conclusions_stated: list[str] = field(default_factory=list)

    # What we don't know
    open_questions: list[str] = field(default_factory=list)
    investigated_paths: list[str] = field(default_factory=list)

    # Where we are
    current_focus: str = "not yet determined"
    session_turn: int = 0
    last_mode_used: str = "none"

    # Full history
    thread: list[SessionEvent] = field(default_factory=list)

    def add_event(self, mode: str, user_input: str, agent_output: str):
        """Call this after every mode execution."""
        self.session_turn += 1
        self.last_mode_used = mode
        event = SessionEvent(
            turn=self.session_turn,
            mode=mode,
            user_input=user_input,
            agent_output=agent_output,
        )
        self.thread.append(event)

    def to_prompt_block(self) -> str:
        """
        Formats the current analytical state as a structured block
        injected into every mode prompt after the ContextBrief.
        This is what gives the agent its memory.
        """
        if self.session_turn == 0:
            return "## ANALYTICAL STATE\nThis is the first call of the session. No prior analysis exists."

        hypotheses_text = "\n".join([
            f"  - [{h.status.upper()}] {h.text} (confidence: {h.confidence:.0%})"
            for h in self.hypotheses
        ]) or "  None yet."

        evidence_text = "\n".join([
            f"  - {e}" for e in self.evidence_collected
        ]) or "  None yet."

        conclusions_text = "\n".join([
            f"  - {c}" for c in self.conclusions_stated
        ]) or "  None yet."

        open_q_text = "\n".join([
            f"  - {q}" for q in self.open_questions
        ]) or "  None yet."

        recent_thread = self.thread[-3:]  # last 3 turns to avoid bloat
        thread_text = "\n".join([
            f"  Turn {e.turn} ({e.mode}): {e.user_input[:80]}..."
            for e in recent_thread
        ])

        return f"""
## ANALYTICAL STATE (session memory — read before responding)
Current Focus: {self.current_focus}
Session Turn: {self.session_turn}
Last Mode Used: {self.last_mode_used}

Hypotheses Tracked:
{hypotheses_text}

Evidence Collected:
{evidence_text}

Conclusions Stated So Far:
{conclusions_text}

Open Questions Flagged:
{open_q_text}

Recent Session Thread (last 3 turns):
{thread_text}
""".strip()