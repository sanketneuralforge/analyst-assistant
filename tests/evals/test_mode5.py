# tests/evals/test_mode5.py

# At top of test_mode4.py and test_mode5.py
import pytest
pytestmark = pytest.mark.slow  # run with: pytest -m slow

import pytest
from modes.mode5_narrative import draft_narrative
from tests.evals.fixtures import (
    get_test_context,
    get_populated_state,
    MODE5_EXEC_INPUT,
    MODE5_DATA_INPUT,
)
from tests.evals.llm_judge import judge
from core.context import ContextBrief


class TestMode5Structure:

    def test_required_fields_present(self):
        result = draft_narrative(
            MODE5_DATA_INPUT,
            get_test_context(),
            get_populated_state(),
        )
        for field in ["narrative", "flags", "what_we_know",
                      "what_we_dont_know", "recommended_next_step"]:
            assert field in result, f"Missing field: {field}"

    def test_narrative_not_empty(self):
        result = draft_narrative(
            MODE5_DATA_INPUT,
            get_test_context(),
            get_populated_state(),
        )
        assert len(result.get("narrative", "")) > 100, \
            "Narrative too short — likely a parse failure"


class TestMode5Behavioral:

    def test_draws_on_session_evidence(self):
        """
        SC5 behavioral: Narrative must reference evidence from state,
        not start fresh as if no analysis had happened.
        """
        state = get_populated_state()
        result = draft_narrative(MODE5_DATA_INPUT, get_test_context(), state)
        narrative = result.get("narrative", "").lower()
        # Check that at least one piece of known evidence appears
        evidence_keywords = ["bot", "deflection", "campaign", "threshold", "june"]
        found = any(kw in narrative for kw in evidence_keywords)
        assert found, "Narrative doesn't reference session evidence — started fresh"


class TestMode5Semantic:

    def test_executive_narrative_avoids_jargon(self):
        """
        SC5 core: Executive narrative must not contain technical jargon.
        Audience-appropriate language is a key thought partner feature.
        """
        exec_context = ContextBrief(
            company_name="Deliveroo Care",
            domain="customer support operations",
            primary_metric="self-serve rate",
            metric_definition="percentage of contacts resolved without an agent",
            time_period="last 30 days",
            audience="executive",
            stakes="board presentation",
            known_context="new bot flow launched June 1st",
            constraints="no competitor benchmarks",
        )
        result = draft_narrative(
            "Write an executive summary of this investigation.",
            exec_context,
            get_populated_state(),
        )
        narrative = result.get("narrative", "")
        verdict = judge(
            output=narrative,
            property_to_evaluate=(
                "Is this narrative free of technical jargon that an executive "
                "without a data background would not understand? Terms like "
                "'confidence threshold', 'deflection rate', 'p-value', "
                "'statistical significance' would be inappropriate. "
                "Plain business language is appropriate."
            ),
        )
        assert verdict["pass"], f"Executive narrative contains jargon: {verdict['reason']}"

    def test_narrative_references_investigation(self):
        """Narrative must synthesise the session, not be generic."""
        result = draft_narrative(
            MODE5_DATA_INPUT,
            get_test_context(),
            get_populated_state(),
        )
        narrative = result.get("narrative", "")
        verdict = judge(
            output=narrative,
            property_to_evaluate=(
                "Does this narrative specifically discuss the self-serve rate "
                "investigation at Deliveroo Care, referencing specific findings "
                "from the analysis? Or is it a generic template that could apply "
                "to any investigation?"
            ),
        )
        assert verdict["pass"], f"Narrative too generic: {verdict['reason']}"