# tests/evals/test_mode3.py

import pytest
from modes.mode3_synthesis import synthesise_docs
from tests.evals.fixtures import (
    get_test_context,
    get_empty_state,
    get_populated_state,
    MODE3_STANDARD_DOCS,
    MODE3_CONTRADICTORY_DOCS,
)
from tests.evals.llm_judge import judge


class TestMode3Structure:

    def test_single_doc_rejected(self):
        """SC3: Fewer than 2 docs must return an error, not a synthesis."""
        result = synthesise_docs(
            ["Only one document."],
            get_test_context(),
            get_empty_state(),
        )
        assert "_error" in result, "Single doc should return error"
        assert result.get("synthesis_summary", "") == ""

    def test_required_fields_present(self):
        result = synthesise_docs(
            MODE3_STANDARD_DOCS,
            get_test_context(),
            get_empty_state(),
        )
        for field in ["facts", "inferences", "gaps", "conflicts", "synthesis_summary"]:
            assert field in result, f"Missing field: {field}"


class TestMode3Behavioral:

    def test_contradiction_detected(self):
        """
        SC3 core: Contradictory documents must surface a conflict.
        False consensus is the most dangerous Mode 3 failure.
        """
        result = synthesise_docs(
            MODE3_CONTRADICTORY_DOCS,
            get_test_context(),
            get_empty_state(),
        )
        assert len(result.get("conflicts", [])) >= 1, \
            "Contradictory documents produced no conflicts — false consensus"

    def test_facts_added_to_state(self):
        """Facts discovered in Mode 3 must appear in state.evidence_collected."""
        state = get_empty_state()
        initial_evidence = len(state.evidence_collected)
        synthesise_docs(MODE3_STANDARD_DOCS, get_test_context(), state)
        assert len(state.evidence_collected) > initial_evidence, \
            "Mode 3 did not write facts to state"

    def test_facts_and_inferences_separated(self):
        """Facts and inferences must be in separate fields — not blended."""
        result = synthesise_docs(
            MODE3_STANDARD_DOCS,
            get_test_context(),
            get_empty_state(),
        )
        assert len(result.get("facts", [])) > 0, "No facts extracted"
        assert len(result.get("inferences", [])) > 0, "No inferences extracted"


class TestMode3Semantic:

    def test_no_false_consensus_on_contradictory_docs(self):
        """LLM judge checks that synthesis doesn't paper over disagreement."""
        result = synthesise_docs(
            MODE3_CONTRADICTORY_DOCS,
            get_test_context(),
            get_empty_state(),
        )
        summary = result.get("synthesis_summary", "")
        verdict = judge(
            output=summary,
            property_to_evaluate=(
                "Does this summary acknowledge that the two sources disagree "
                "about the cause of the self-serve rate drop? Or does it "
                "present a false consensus as if both sources agree?"
            ),
        )
        assert verdict["pass"], f"False consensus produced: {verdict['reason']}"