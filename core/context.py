# core/context.py

from dataclasses import dataclass, field


@dataclass
class ContextBrief:
    # WHO you are
    company_name: str
    domain: str                    # "customer support operations"

    # WHAT you're analysing
    primary_metric: str            # "self-serve rate"
    metric_definition: str         # "% of contacts resolved without agent"
    time_period: str               # "last 30 days"

    # WHO reads the output
    audience: str                  # "executive" | "data team" | "ops manager"
    stakes: str                    # "weekly leadership review"

    # WHAT the agent should know upfront
    known_context: str             # "we launched a new bot flow on June 1"
    constraints: str               # "do not reference competitor benchmarks"

    def to_prompt_block(self) -> str:
        """
        Formats the brief as a structured block injected at the
        top of every mode prompt. The model reads this first,
        before any instructions or user input.
        """
        return f"""
                    ## ANALYTICAL CONTEXT (read this before anything else)
                    - Company / Team: {self.company_name}
                    - Domain: {self.domain}
                    - Primary Metric: {self.primary_metric}
                    - Metric Definition: {self.metric_definition}
                    - Time Period Under Analysis: {self.time_period}
                    - Output Audience: {self.audience}
                    - Stakes: {self.stakes}
                    - Known Context: {self.known_context}
                    - Constraints: {self.constraints}
                    """.strip()