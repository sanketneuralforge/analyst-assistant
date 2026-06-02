# tests/evals/test_mode1.py

import pytest
from modes.mode1_hypotheses import generate_hypotheses
from tests.evals.fixtures import (
    get_test_context,
    get_empty_state,
    MODE1_STANDARD_INPUT,
    MODE1_VAGUE_INPUT,
)
from tests.evals.llm_judge import judge


class TestMode1Structure:
    """Level 1 — Structural evals. Deterministic."""

    def test_output_is_parseable(self):
        """SC1a: Output must be valid JSON, not a parse error."""
        result = generate_hypotheses(
            MODE1_STANDARD_INPUT,
            get_test_context(),
            get_empty_state(),
        )
        assert "_raw" not in result or result.get("hypotheses"), \
            "Output failed to parse — raw output returned"

    def test_required_fields_present(self):
        """SC1b: All required fields must be in output."""
        result = generate_hypotheses(
            MODE1_STANDARD_INPUT,
            get_test_context(),
            get_empty_state(),
        )
        required = ["hypotheses", "open_questions", "current_focus_update"]
        for field in required:
            assert field in result, f"Missing required field: {field}"

    def test_generates_at_least_two_hypotheses(self):
        """SC1c: Must generate at least 2 hypotheses."""
        result = generate_hypotheses(
            MODE1_STANDARD_INPUT,
            get_test_context(),
            get_empty_state(),
        )
        assert len(result.get("hypotheses", [])) >= 2, \
            f"Only {len(result.get('hypotheses', []))} hypotheses generated"

    def test_confidence_scores_are_valid(self):
        """SC1d: Confidence must be between 0.0 and 1.0."""
        result = generate_hypotheses(
            MODE1_STANDARD_INPUT,
            get_test_context(),
            get_empty_state(),
        )
        for h in result.get("hypotheses", []):
            c = h.get("confidence", -1)
            assert 0.0 <= c <= 1.0, f"Invalid confidence score: {c}"

    def test_confidence_scores_are_differentiated(self):
        """SC1e: Not all hypotheses should have identical confidence."""
        result = generate_hypotheses(
            MODE1_STANDARD_INPUT,
            get_test_context(),
            get_empty_state(),
        )
        scores = [h.get("confidence") for h in result.get("hypotheses", [])]
        assert len(set(scores)) > 1, \
            "All hypotheses have identical confidence — model is not reasoning"

    def test_open_questions_generated(self):
        """SC1f: At least one open question must be flagged."""
        result = generate_hypotheses(
            MODE1_STANDARD_INPUT,
            get_test_context(),
            get_empty_state(),
        )
        assert len(result.get("open_questions", [])) >= 1


class TestMode1Behavioral:
    """Level 2 — Behavioral evals."""

    def test_no_hallucinated_metrics(self):
        """
        SC1 core: Every hypothesis must cite a metric from the input.
        This is the hardest behavioral test — hallucinated metrics
        are the most common Mode 1 failure in production.
        """
        provided_metrics = [
            "bot_deflection_rate",
            "avg_handle_time",
            "contact_volume",
        ]
        result = generate_hypotheses(
            MODE1_STANDARD_INPUT,
            get_test_context(),
            get_empty_state(),
        )
        for h in result.get("hypotheses", []):
            cited = h.get("co_moving_metric_cited", "")
            # Check that the cited metric is a substring of one of the provided ones
            cited_lower = cited.lower().replace(" ", "_")
            is_valid = any(
                m in cited_lower or cited_lower in m
                for m in provided_metrics
            )
            assert is_valid, \
                f"Hallucinated metric cited: '{cited}' not in {provided_metrics}"

    def test_state_updated_after_call(self):
        """SC1g: AnalyticalState must be updated after Mode 1 runs."""
        state = get_empty_state()
        assert len(state.hypotheses) == 0
        generate_hypotheses(MODE1_STANDARD_INPUT, get_test_context(), state)
        assert len(state.hypotheses) > 0, "State not updated after Mode 1"
        assert state.session_turn == 1
        assert state.current_focus != "not yet determined"


class TestMode1Semantic:
    """Level 3 — Semantic evals using LLM judge."""

    def test_hypotheses_are_specific_not_generic(self):
        """Hypotheses should be specific to the metric context, not generic."""
        result = generate_hypotheses(
            MODE1_STANDARD_INPUT,
            get_test_context(),
            get_empty_state(),
        )
        hypotheses_text = str(result.get("hypotheses", []))
        verdict = judge(
            output=hypotheses_text,
            property_to_evaluate=(
                "Are these hypotheses specific to the self-serve rate metric "
                "in a customer support context, or are they generic enough to "
                "apply to any metric in any domain? They should be specific."
            ),
        )
        assert verdict["pass"], f"Hypotheses too generic: {verdict['reason']}"