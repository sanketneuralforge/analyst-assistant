# tests/evals/test_mode4.py

# At top of test_mode4.py and test_mode5.py
import pytest
pytestmark = pytest.mark.slow  # run with: pytest -m slow

import pytest
from modes.mode4_stress import stress_test_conclusion
from tests.evals.fixtures import (
    get_test_context,
    get_populated_state,
    MODE4_WEAK_CONCLUSION,
)
from tests.evals.llm_judge import judge


class TestMode4Structure:

    def test_required_fields_present(self):
        result = stress_test_conclusion(
            MODE4_WEAK_CONCLUSION,
            get_test_context(),
            get_populated_state(),
        )
        for field in ["verdict", "flaws", "hypotheses_referenced",
                      "verdict_reason", "strengthening_analysis"]:
            assert field in result, f"Missing field: {field}"

    def test_verdict_is_valid_value(self):
        result = stress_test_conclusion(
            MODE4_WEAK_CONCLUSION,
            get_test_context(),
            get_populated_state(),
        )
        assert result.get("verdict") in ["STRONG", "NEEDS WORK", "UNSUPPORTED"], \
            f"Invalid verdict: {result.get('verdict')}"


class TestMode4Behavioral:

    def test_weak_conclusion_not_rated_strong(self):
        """
        SC4 core: A conclusion that ignores alternative explanations
        must not receive a STRONG verdict.
        """
        result = stress_test_conclusion(
            MODE4_WEAK_CONCLUSION,
            get_test_context(),
            get_populated_state(),
        )
        assert result.get("verdict") != "STRONG", \
            "Weak conclusion rated STRONG — stress tester is not working"

    def test_references_session_hypotheses(self):
        """
        SC7: Mode 4 must reference hypotheses from the analytical state,
        not generate new ones from scratch.
        """
        state = get_populated_state()
        hypothesis_texts = {h.text for h in state.hypotheses}
        result = stress_test_conclusion(
            MODE4_WEAK_CONCLUSION,
            get_test_context(),
            state,
        )
        referenced = result.get("hypotheses_referenced", [])
        assert len(referenced) >= 1, "No hypotheses referenced from state"

        # At least one referenced hypothesis should overlap with state
        overlap = any(
            any(word in ref for word in h.split()[:4])
            for ref in referenced
            for h in hypothesis_texts
        )
        assert overlap, \
            f"Referenced hypotheses don't match state: {referenced}"

    def test_at_least_two_flaws_identified(self):
        """SC4: Must identify at least 2 flaws."""
        result = stress_test_conclusion(
            MODE4_WEAK_CONCLUSION,
            get_test_context(),
            get_populated_state(),
        )
        assert len(result.get("flaws", [])) >= 2, \
            f"Only {len(result.get('flaws', []))} flaw(s) identified"

    def test_conclusion_logged_to_state(self):
        """Stress-tested conclusions must be recorded in state."""
        state = get_populated_state()
        initial = len(state.conclusions_stated)
        stress_test_conclusion(MODE4_WEAK_CONCLUSION, get_test_context(), state)
        assert len(state.conclusions_stated) > initial


class TestMode4Semantic:

    def test_flaws_are_specific_not_generic(self):
        """Flaws should reference the specific analytical context."""
        result = stress_test_conclusion(
            MODE4_WEAK_CONCLUSION,
            get_test_context(),
            get_populated_state(),
        )
        flaws_text = str(result.get("flaws", []))
        verdict = judge(
            output=flaws_text,
            property_to_evaluate=(
                "Are these flaws specific to the bot deflection / self-serve "
                "rate investigation, or are they generic critiques that could "
                "apply to any conclusion in any domain?"
            ),
        )
        assert verdict["pass"], f"Flaws too generic: {verdict['reason']}"