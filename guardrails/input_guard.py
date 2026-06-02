# guardrails/input_guard.py

"""
Input validation for all five modes.

Each mode has different minimum requirements. Validating before
calling the LLM saves tokens and gives better error messages
than letting the LLM produce a confused output.
"""

from dataclasses import dataclass
from guardrails.injection_guard import check_injection


@dataclass
class ValidationResult:
    is_valid: bool
    error: str = ""
    warning: str = ""


def validate_mode1_input(text: str) -> ValidationResult:
    """
    Mode 1 needs a meaningful metric description.
    Vague inputs produce vague hypotheses.
    """
    if not text or len(text.strip()) < 30:
        return ValidationResult(
            is_valid=False,
            error="Input too short. Describe the metric pattern in at least a sentence, including the metric name and direction of change."
        )

    # Check for injection
    is_safe, reason = check_injection(text)
    if not is_safe:
        return ValidationResult(is_valid=False, error=reason)

    # Warn if no numbers provided — hypotheses will be less specific
    has_numbers = any(char.isdigit() for char in text)
    warning = "" if has_numbers else (
        "Tip: including specific numbers (e.g. 'dropped from 68% to 54%') "
        "produces more targeted hypotheses."
    )

    return ValidationResult(is_valid=True, warning=warning)


def validate_mode2_input(text: str) -> ValidationResult:
    """
    Mode 2 needs a clear investigation request.
    """
    if not text or len(text.strip()) < 20:
        return ValidationResult(
            is_valid=False,
            error="Describe what you want to investigate with code."
        )

    is_safe, reason = check_injection(text)
    if not is_safe:
        return ValidationResult(is_valid=False, error=reason)

    # Warn if no dataframe/table mentioned
    has_data_ref = any(
        word in text.lower()
        for word in ["dataframe", "df", "table", "column", "csv",
                     "database", "sql", "query", "contacts", "events"]
    )
    warning = "" if has_data_ref else (
        "Tip: mention your dataframe name and column names "
        "for more accurate code generation."
    )

    return ValidationResult(is_valid=True, warning=warning)


def validate_mode3_input(documents: list[str]) -> ValidationResult:
    """
    Mode 3 requires at least 2 non-trivial documents.
    """
    non_empty = [d for d in documents if d and len(d.strip()) > 20]

    if len(non_empty) < 2:
        return ValidationResult(
            is_valid=False,
            error="Provide at least 2 source documents with meaningful content."
        )

    # Check all docs for injection
    for i, doc in enumerate(non_empty, 1):
        is_safe, reason = check_injection(doc)
        if not is_safe:
            return ValidationResult(
                is_valid=False,
                error=f"Source {i} flagged: {reason}"
            )

    # Warn if all docs are very similar length — may be duplicates
    lengths = [len(d) for d in non_empty]
    if len(set(lengths)) == 1 and len(non_empty) > 1:
        return ValidationResult(
            is_valid=True,
            warning="All documents are the same length — check they are not duplicates."
        )

    return ValidationResult(is_valid=True)


def validate_mode4_input(text: str) -> ValidationResult:
    """
    Mode 4 needs a stated conclusion — not a question.
    """
    if not text or len(text.strip()) < 20:
        return ValidationResult(
            is_valid=False,
            error="State a conclusion to stress-test. Mode 4 challenges conclusions, not questions."
        )

    is_safe, reason = check_injection(text)
    if not is_safe:
        return ValidationResult(is_valid=False, error=reason)

    # Warn if input looks like a question rather than a conclusion
    stripped = text.strip()
    if stripped.endswith("?"):
        return ValidationResult(
            is_valid=True,
            warning="This looks like a question. Mode 4 works best with a stated conclusion (e.g. 'The drop was caused by X')."
        )

    return ValidationResult(is_valid=True)


def validate_mode5_input(text: str) -> ValidationResult:
    """
    Mode 5 focus is optional — empty is fine.
    """
    if not text or not text.strip():
        return ValidationResult(is_valid=True)

    is_safe, reason = check_injection(text)
    if not is_safe:
        return ValidationResult(is_valid=False, error=reason)

    return ValidationResult(is_valid=True)


def validate_context_block(text: str) -> ValidationResult:
    """
    Validate the analyst context block before indexing into ChromaDB.
    """
    if not text or not text.strip():
        return ValidationResult(is_valid=True)

    if len(text) > 50000:
        return ValidationResult(
            is_valid=False,
            error="Context block too large (max 50,000 characters). Split into multiple sessions or upload as a file."
        )

    is_safe, reason = check_injection(text)
    if not is_safe:
        return ValidationResult(is_valid=False, error=reason)

    return ValidationResult(is_valid=True)