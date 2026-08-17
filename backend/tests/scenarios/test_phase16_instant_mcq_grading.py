"""
Scenario tests — Phase 16: Instant MCQ grading (no LLM call).

Given/When/Then pattern, SQLite in-memory DB, no live API calls.
"""

from __future__ import annotations

import pytest
from app.api.routes.learning_paths import _grade_mcq_instantly
from app.schemas.items import GraderOutput, MCQAnswerKey


# ── Helpers ────────────────────────────────────────────────────────────────────

_BASE_ANSWER_KEY = {
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_index": 0,
    "trap_index": 2,
    "correct_rationale": "Correct — Option A is right because it applies X correctly.",
    "incorrect_rationale": "The correct answer is Option A. Option A is right because it applies X correctly.",
}


def _key(**overrides) -> dict:
    return {**_BASE_ANSWER_KEY, **overrides}


# ── Phase 16: _grade_mcq_instantly ────────────────────────────────────────────

class TestGradeMcqInstantly:
    """Unit tests for the deterministic MCQ grading helper."""

    def test_correct_answer_scores_1(self):
        """Given selected_index == correct_index, score is 1.0."""
        result = _grade_mcq_instantly(_key(), {"selected_index": 0})
        assert result is not None
        assert result.score == 1.0

    def test_incorrect_answer_scores_0(self):
        """Given selected_index != correct_index, score is 0.0."""
        result = _grade_mcq_instantly(_key(), {"selected_index": 1})
        assert result is not None
        assert result.score == 0.0

    def test_correct_answer_returns_correct_rationale(self):
        """Correct answer response carries correct_rationale as grader_rationale."""
        result = _grade_mcq_instantly(_key(), {"selected_index": 0})
        assert result is not None
        assert result.grader_rationale == _BASE_ANSWER_KEY["correct_rationale"]

    def test_incorrect_answer_returns_incorrect_rationale(self):
        """Wrong answer response carries incorrect_rationale as grader_rationale."""
        result = _grade_mcq_instantly(_key(), {"selected_index": 1})
        assert result is not None
        assert result.grader_rationale == _BASE_ANSWER_KEY["incorrect_rationale"]

    def test_trap_selection_flagged(self):
        """Selecting the trap option sets is_trap_selected=True."""
        result = _grade_mcq_instantly(_key(), {"selected_index": 2})  # trap_index=2
        assert result is not None
        assert result.score == 0.0
        assert result.is_trap_selected is True

    def test_non_trap_wrong_answer_not_flagged(self):
        """Selecting a wrong but non-trap option sets is_trap_selected=False.

        None means "not applicable" (correct answer or free-text).
        False means "MCQ answered incorrectly, but not via the trap option".
        """
        # selected_index=1 is wrong (correct=0) and not the trap (trap=2)
        result = _grade_mcq_instantly(_key(), {"selected_index": 1})
        assert result is not None
        assert result.is_trap_selected is False

    def test_correct_answer_is_trap_selected_none(self):
        """is_trap_selected is None when the answer is correct (trap not applicable)."""
        result = _grade_mcq_instantly(_key(), {"selected_index": 0})
        assert result is not None
        assert result.is_trap_selected is None

    def test_no_trap_index_wrong_answer_returns_none(self):
        """When trap_index is None, is_trap_selected is None regardless of answer."""
        ak = _key(trap_index=None)
        result = _grade_mcq_instantly(ak, {"selected_index": 1})
        assert result is not None
        assert result.is_trap_selected is None

    def test_returns_none_when_correct_rationale_missing(self):
        """Legacy items without correct_rationale return None → GraderAgent fallback."""
        ak = _key(correct_rationale=None)
        result = _grade_mcq_instantly(ak, {"selected_index": 0})
        assert result is None

    def test_returns_none_when_incorrect_rationale_missing(self):
        """Legacy items without incorrect_rationale return None → GraderAgent fallback."""
        ak = _key(incorrect_rationale=None)
        result = _grade_mcq_instantly(ak, {"selected_index": 1})
        assert result is None

    def test_returns_none_when_both_rationales_missing(self):
        """Items with no Phase 16 rationales at all return None → GraderAgent fallback."""
        ak = {
            "options": ["A", "B", "C", "D"],
            "correct_index": 0,
            "trap_index": 1,
        }
        result = _grade_mcq_instantly(ak, {"selected_index": 0})
        assert result is None

    def test_returns_none_for_missing_selected_index(self):
        """Malformed response without selected_index falls back to GraderAgent."""
        result = _grade_mcq_instantly(_key(), {"text": "Some answer"})
        assert result is None

    def test_returns_grader_output_instance(self):
        """Return type is GraderOutput when grading succeeds."""
        result = _grade_mcq_instantly(_key(), {"selected_index": 0})
        assert isinstance(result, GraderOutput)

    def test_score_boundaries_are_exact(self):
        """MCQ score is exactly 1.0 or 0.0 — no partial credit."""
        correct = _grade_mcq_instantly(_key(), {"selected_index": 0})
        wrong = _grade_mcq_instantly(_key(), {"selected_index": 3})
        assert correct is not None and correct.score == 1.0
        assert wrong is not None and wrong.score == 0.0

    def test_works_with_all_four_option_indices(self):
        """Grading handles any valid selected_index (0–3)."""
        for idx in range(4):
            result = _grade_mcq_instantly(_key(correct_index=idx), {"selected_index": idx})
            assert result is not None
            assert result.score == 1.0

    def test_correct_when_correct_index_is_last_option(self):
        """Correct answer at index 3 (last) still scores 1.0."""
        ak = _key(correct_index=3, trap_index=1)
        result = _grade_mcq_instantly(ak, {"selected_index": 3})
        assert result is not None
        assert result.score == 1.0
        assert result.is_trap_selected is None


# ── MCQAnswerKey schema evolution ─────────────────────────────────────────────

class TestMCQAnswerKeySchema:
    """Verify the Phase 16 MCQAnswerKey fields are optional (backward compat)."""

    def test_legacy_key_validates_without_rationales(self):
        """MCQAnswerKey without rationale fields is valid (legacy support)."""
        ak = MCQAnswerKey(options=["A", "B", "C", "D"], correct_index=0)
        assert ak.correct_rationale is None
        assert ak.incorrect_rationale is None

    def test_full_phase16_key_validates(self):
        """MCQAnswerKey with both rationale fields validates correctly."""
        ak = MCQAnswerKey(
            options=["A", "B", "C", "D"],
            correct_index=1,
            trap_index=2,
            correct_rationale="Yes, B is right because ...",
            incorrect_rationale="The correct answer is B because ...",
        )
        assert ak.correct_rationale is not None
        assert ak.incorrect_rationale is not None

    def test_model_dump_includes_rationale_fields(self):
        """model_dump() includes rationale fields (important for DB persistence)."""
        ak = MCQAnswerKey(
            options=["A", "B", "C", "D"],
            correct_index=0,
            correct_rationale="Good job",
            incorrect_rationale="Wrong",
        )
        dumped = ak.model_dump()
        assert "correct_rationale" in dumped
        assert "incorrect_rationale" in dumped
        assert dumped["correct_rationale"] == "Good job"

    def test_validate_from_dict_legacy(self):
        """model_validate works on legacy dicts (missing rationale fields)."""
        raw = {"options": ["A", "B", "C", "D"], "correct_index": 0, "trap_index": 1}
        ak = MCQAnswerKey.model_validate(raw)
        assert ak.correct_rationale is None
        assert ak.incorrect_rationale is None
