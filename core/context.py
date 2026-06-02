# core/context.py

from dataclasses import dataclass, field


@dataclass
class ContextBrief:
    # WHO you are
    company_name: str
    domain: str

    # WHAT you're analysing
    primary_metric: str
    metric_definition: str
    time_period: str

    # WHO reads the output
    audience: str
    stakes: str

    # WHAT the agent should know upfront (short, structured)
    known_context: str
    constraints: str

    # NEW: free-form analytical context block
    # Longer, unstructured — metric quirks, schema notes,
    # business rules, anything the analyst wants the agent to know
    analyst_context: str = ""

    def to_prompt_block(self) -> str:
        base = f"""
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

        # Append analyst context block if provided
        if self.analyst_context.strip():
            base += f"""

## ANALYST-PROVIDED CONTEXT
{self.analyst_context.strip()}
"""
        return base