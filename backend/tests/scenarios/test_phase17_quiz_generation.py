"""
Scenario tests — Phase 17: Continuous Quiz Generation on Path Create & Exhaustion-Aware Refresh.

Given/When/Then pattern, SQLite in-memory DB for DB-touching tests.
All tests use the db_session fixture (no live API / Postgres needed).
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.learning_paths import (
    _assign_question_counts,
    _check_quiz_exhaustion,
    _compute_skill_avg_scores,
)
from app.agents.quiz_batch_generator import SkillQuizSpec
from app.db.models import Attempt, Item, Skill


# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_skill_id() -> str:
    return str(uuid.uuid4())


def _make_practitioner_id() -> str:
    return str(uuid.uuid4())


async def _insert_item(db: AsyncSession, skill_id: str, prompt: str = "Q?") -> str:
    """Insert a minimal Item row and return its ID."""
    item_id = str(uuid.uuid4())
    db.add(Item(
        id=item_id,
        skill_id=skill_id,
        item_type="mcq",
        prompt=prompt,
        answer_key={"options": ["A", "B", "C", "D"], "correct_index": 0, "trap_index": 1},
        difficulty=0.5,
        calibration_stats={"attempt_count": 0, "total_score": 0.0, "trap_selection_count": 0},
        generation=1,
    ))
    await db.flush()
    return item_id


async def _insert_attempt(
    db: AsyncSession,
    practitioner_id: str,
    item_id: str,
    score: float = 1.0,
) -> str:
    """Insert a minimal Attempt row and return its ID."""
    attempt_id = str(uuid.uuid4())
    from datetime import UTC, datetime
    db.add(Attempt(
        id=attempt_id,
        practitioner_id=practitioner_id,
        item_id=item_id,
        response={"selected_index": 0},
        score=score,
        grader_rationale="Test rationale.",
        attempted_at=datetime.now(UTC),
    ))
    await db.flush()
    return attempt_id


def _make_spec(*, is_cert_evaluated: bool = False) -> SkillQuizSpec:
    return SkillQuizSpec(
        skill_id=_make_skill_id(),
        skill_name="Test Skill",
        mastery_score=0.4,
        is_cert_evaluated=is_cert_evaluated,
    )


# ── _check_quiz_exhaustion ────────────────────────────────────────────────────


class TestCheckQuizExhaustion:
    """
    Tests for the quiz exhaustion detection helper.
    """

    async def test_no_items_returns_first_generation(self, db_session: AsyncSession):
        """
        Scenario: No items exist for the path's skills.
          Given a practitioner and skill IDs with no items in the DB
          When _check_quiz_exhaustion is called
          Then it returns (True, True) — should generate, is first time
        """
        practitioner_id = _make_practitioner_id()
        skill_ids = [_make_skill_id(), _make_skill_id()]

        should_gen, is_first = await _check_quiz_exhaustion(
            practitioner_id, skill_ids, db_session
        )

        assert should_gen is True
        assert is_first is True

    async def test_unanswered_items_returns_skip(self, db_session: AsyncSession):
        """
        Scenario: Some items exist but none have been attempted.
          Given items exist for the skill IDs
          When _check_quiz_exhaustion is called with no attempts
          Then it returns (False, False) — skip generation, not first time
        """
        practitioner_id = _make_practitioner_id()
        skill_id = _make_skill_id()

        await _insert_item(db_session, skill_id, "Question A?")
        await _insert_item(db_session, skill_id, "Question B?")

        should_gen, is_first = await _check_quiz_exhaustion(
            practitioner_id, [skill_id], db_session
        )

        assert should_gen is False
        assert is_first is False

    async def test_partially_answered_items_returns_skip(self, db_session: AsyncSession):
        """
        Scenario: Some items answered, some not.
          Given 3 items for a skill, practitioner attempted 2
          When _check_quiz_exhaustion is called
          Then it returns (False, False) — still has unanswered items
        """
        practitioner_id = _make_practitioner_id()
        skill_id = _make_skill_id()

        item1 = await _insert_item(db_session, skill_id, "Q1?")
        item2 = await _insert_item(db_session, skill_id, "Q2?")
        item3 = await _insert_item(db_session, skill_id, "Q3?")

        await _insert_attempt(db_session, practitioner_id, item1)
        await _insert_attempt(db_session, practitioner_id, item2)
        # item3 not attempted

        should_gen, is_first = await _check_quiz_exhaustion(
            practitioner_id, [skill_id], db_session
        )

        assert should_gen is False
        assert is_first is False

    async def test_all_items_answered_returns_exhausted(self, db_session: AsyncSession):
        """
        Scenario: All items have been attempted by this practitioner.
          Given 2 items for a skill, both attempted
          When _check_quiz_exhaustion is called
          Then it returns (True, False) — should generate, not first time
        """
        practitioner_id = _make_practitioner_id()
        skill_id = _make_skill_id()

        item1 = await _insert_item(db_session, skill_id, "Q1?")
        item2 = await _insert_item(db_session, skill_id, "Q2?")

        await _insert_attempt(db_session, practitioner_id, item1)
        await _insert_attempt(db_session, practitioner_id, item2)

        should_gen, is_first = await _check_quiz_exhaustion(
            practitioner_id, [skill_id], db_session
        )

        assert should_gen is True
        assert is_first is False

    async def test_empty_skill_ids_returns_false(self, db_session: AsyncSession):
        """
        Scenario: No skill IDs passed.
          Given an empty skill_ids list
          When _check_quiz_exhaustion is called
          Then it returns (False, False) — nothing to generate
        """
        practitioner_id = _make_practitioner_id()

        should_gen, is_first = await _check_quiz_exhaustion(
            practitioner_id, [], db_session
        )

        assert should_gen is False
        assert is_first is False

    async def test_other_practitioner_attempts_do_not_count(self, db_session: AsyncSession):
        """
        Scenario: Another practitioner answered all items, but the current one has not.
          Given items attempted by a different practitioner
          When _check_quiz_exhaustion is called for the current practitioner
          Then it returns (False, False) — their own attempts are zero
        """
        practitioner_id = _make_practitioner_id()
        other_practitioner_id = _make_practitioner_id()
        skill_id = _make_skill_id()

        item1 = await _insert_item(db_session, skill_id, "Q1?")
        item2 = await _insert_item(db_session, skill_id, "Q2?")

        # Only the OTHER practitioner has attempted these
        await _insert_attempt(db_session, other_practitioner_id, item1)
        await _insert_attempt(db_session, other_practitioner_id, item2)

        should_gen, is_first = await _check_quiz_exhaustion(
            practitioner_id, [skill_id], db_session
        )

        # Items exist (not first time), but THIS practitioner hasn't answered them
        assert should_gen is False
        assert is_first is False


# ── _assign_question_counts ───────────────────────────────────────────────────


class TestAssignQuestionCounts:
    """
    Tests for the question-count assignment helper (pure function, no DB).
    """

    def test_total_in_range_10_to_12(self):
        """
        Scenario: Normal path with 8 skills.
          Given 8 skill specs
          When _assign_question_counts is called
          Then total question_count sum is between 10 and 12
        """
        specs = [_make_spec() for _ in range(8)]
        _assign_question_counts(specs)
        total = sum(s.question_count for s in specs)
        assert 10 <= total <= 12

    def test_each_skill_gets_1_or_2(self):
        """
        Scenario: Each skill gets exactly 1 or 2 questions.
          Given 10 skill specs
          When _assign_question_counts is called
          Then every spec has question_count of 1 or 2
        """
        specs = [_make_spec() for _ in range(10)]
        _assign_question_counts(specs)
        for spec in specs:
            assert spec.question_count in (1, 2)

    def test_cert_skills_prioritised_for_double_slots(self):
        """
        Scenario: Cert-evaluated skills are preferred for 2-question slots.
          Given 4 cert skills and 4 supplementary skills (8 total)
          When _assign_question_counts runs 100 times
          Then cert skills accumulate more double-question assignments than supp skills
          (With 8 skills: lo=10, hi=12, extra=2-4; cert slots filled before supp)
        """
        cert_doubles = 0
        supp_doubles = 0
        trials = 100
        for _ in range(trials):
            cert_specs = [_make_spec(is_cert_evaluated=True) for _ in range(4)]
            supp_specs = [_make_spec(is_cert_evaluated=False) for _ in range(4)]
            all_specs = cert_specs + supp_specs
            _assign_question_counts(all_specs, target_min=10, target_max=12)
            cert_doubles += sum(1 for s in cert_specs if s.question_count == 2)
            supp_doubles += sum(1 for s in supp_specs if s.question_count == 2)

        # Cert skills should be getting 2-question slots far more often (they're always filled first)
        assert cert_doubles > supp_doubles

    def test_small_path_fewer_than_10_skills_gets_extras(self):
        """
        Scenario: Path with only 5 skills — extras needed to reach 10.
          Given 5 skill specs
          When _assign_question_counts is called
          Then total is between 10 and 10 (capped at 10 = 5×2)
        """
        specs = [_make_spec() for _ in range(5)]
        _assign_question_counts(specs)
        total = sum(s.question_count for s in specs)
        # With 5 skills, lo=max(10,5)=10, hi=min(12,10)=10, so target=10 always
        assert total == 10
        # All 5 skills must have question_count=2 to reach 10
        for spec in specs:
            assert spec.question_count == 2

    def test_large_path_more_than_12_skills_gives_one_each(self):
        """
        Scenario: Path with 15 skills — can't reach 10-12 without going to 3.
          Given 15 skill specs
          When _assign_question_counts is called
          Then each skill gets question_count=1 (safe fallback)
        """
        specs = [_make_spec() for _ in range(15)]
        _assign_question_counts(specs)
        # lo=15 > hi=12, so fallback: all get 1
        for spec in specs:
            assert spec.question_count == 1

    def test_empty_specs_does_not_crash(self):
        """
        Scenario: Empty specs list.
          Given no skill specs
          When _assign_question_counts is called
          Then no exception is raised
        """
        specs: list = []
        _assign_question_counts(specs)  # Should not raise


# ── _compute_skill_avg_scores ─────────────────────────────────────────────────


class TestComputeSkillAvgScores:
    """
    Tests for per-skill average score computation.
    """

    async def test_returns_correct_averages(self, db_session: AsyncSession):
        """
        Scenario: Two skills, multiple attempts each.
          Given skill_a with attempts scoring 1.0, 0.0 (avg=0.5)
          And skill_b with attempts scoring 1.0, 1.0 (avg=1.0)
          When _compute_skill_avg_scores is called
          Then it returns {skill_a: 0.5, skill_b: 1.0}
        """
        practitioner_id = _make_practitioner_id()
        skill_a = _make_skill_id()
        skill_b = _make_skill_id()

        item_a1 = await _insert_item(db_session, skill_a, "QA1?")
        item_a2 = await _insert_item(db_session, skill_a, "QA2?")
        item_b1 = await _insert_item(db_session, skill_b, "QB1?")
        item_b2 = await _insert_item(db_session, skill_b, "QB2?")

        await _insert_attempt(db_session, practitioner_id, item_a1, score=1.0)
        await _insert_attempt(db_session, practitioner_id, item_a2, score=0.0)
        await _insert_attempt(db_session, practitioner_id, item_b1, score=1.0)
        await _insert_attempt(db_session, practitioner_id, item_b2, score=1.0)

        result = await _compute_skill_avg_scores(
            practitioner_id, [skill_a, skill_b], db_session
        )

        assert skill_a in result
        assert skill_b in result
        assert abs(result[skill_a] - 0.5) < 0.001
        assert abs(result[skill_b] - 1.0) < 0.001

    async def test_only_counts_this_practitioner(self, db_session: AsyncSession):
        """
        Scenario: Other practitioners' attempts do not affect averages.
          Given skill with practitioner scoring 1.0 and other scoring 0.0
          When _compute_skill_avg_scores is called for the practitioner
          Then only the practitioner's 1.0 is included
        """
        practitioner_id = _make_practitioner_id()
        other_id = _make_practitioner_id()
        skill_id = _make_skill_id()

        item1 = await _insert_item(db_session, skill_id, "Q1?")
        item2 = await _insert_item(db_session, skill_id, "Q2?")

        await _insert_attempt(db_session, practitioner_id, item1, score=1.0)
        await _insert_attempt(db_session, other_id, item2, score=0.0)

        result = await _compute_skill_avg_scores(
            practitioner_id, [skill_id], db_session
        )

        assert skill_id in result
        assert abs(result[skill_id] - 1.0) < 0.001

    async def test_skill_with_no_attempts_absent_from_result(self, db_session: AsyncSession):
        """
        Scenario: Skill with items but no attempts.
          Given a skill with items but zero attempts by this practitioner
          When _compute_skill_avg_scores is called
          Then that skill is absent from the result dict
        """
        practitioner_id = _make_practitioner_id()
        skill_id = _make_skill_id()

        await _insert_item(db_session, skill_id, "Q1?")

        result = await _compute_skill_avg_scores(
            practitioner_id, [skill_id], db_session
        )

        assert skill_id not in result


# ── Difficulty adjustment logic ───────────────────────────────────────────────


class TestDifficultyAdjustment:
    """
    Tests for the per-skill mastery adjustment applied during exhaustion refresh.
    These test the logic inline (extracted from _run_quiz_batch_for_path).
    """

    def _adjust(self, mastery: float, avg: float | None) -> float:
        """Reproduce the difficulty adjustment logic from _run_quiz_batch_for_path."""
        if avg is not None:
            if avg >= 1.0:
                mastery = min(mastery + 0.25, 0.95)
            elif avg < 0.5:
                mastery = max(mastery - 0.10, 0.05)
        return mastery

    def test_perfect_score_bumps_mastery_up(self):
        """
        Scenario: Practitioner got 100% on all items for a skill.
          Given avg_score == 1.0 and mastery == 0.5
          When difficulty adjustment is applied
          Then mastery is bumped up by 0.25 to 0.75
        """
        result = self._adjust(mastery=0.5, avg=1.0)
        assert abs(result - 0.75) < 0.001

    def test_perfect_score_capped_at_0_95(self):
        """
        Scenario: Practitioner already at 0.80 mastery with perfect score.
          Given avg_score == 1.0 and mastery == 0.80
          When difficulty adjustment is applied
          Then mastery is capped at 0.95 (not 1.05)
        """
        result = self._adjust(mastery=0.80, avg=1.0)
        assert abs(result - 0.95) < 0.001

    def test_poor_score_reduces_mastery(self):
        """
        Scenario: Practitioner scored below 50% on skill items.
          Given avg_score == 0.3 and mastery == 0.5
          When difficulty adjustment is applied
          Then mastery is reduced by 0.10 to 0.40
        """
        result = self._adjust(mastery=0.5, avg=0.3)
        assert abs(result - 0.40) < 0.001

    def test_poor_score_floored_at_0_05(self):
        """
        Scenario: Very low mastery with poor score.
          Given avg_score == 0.0 and mastery == 0.08
          When difficulty adjustment is applied
          Then mastery is floored at 0.05 (not negative)
        """
        result = self._adjust(mastery=0.08, avg=0.0)
        assert abs(result - 0.05) < 0.001

    def test_mid_range_score_unchanged(self):
        """
        Scenario: Practitioner scored in the 50-99% range.
          Given avg_score == 0.7 and mastery == 0.5
          When difficulty adjustment is applied
          Then mastery is unchanged at 0.5
        """
        result = self._adjust(mastery=0.5, avg=0.7)
        assert abs(result - 0.5) < 0.001

    def test_exactly_50_percent_is_unchanged(self):
        """
        Scenario: Boundary case — exactly 0.5 avg score.
          Given avg_score == 0.5 (not < 0.5)
          When difficulty adjustment is applied
          Then mastery is unchanged
        """
        result = self._adjust(mastery=0.6, avg=0.5)
        assert abs(result - 0.6) < 0.001

    def test_none_avg_leaves_mastery_unchanged(self):
        """
        Scenario: avg_score_by_skill is None (first generation).
          Given avg is None
          When difficulty adjustment is applied
          Then mastery is completely unchanged
        """
        result = self._adjust(mastery=0.4, avg=None)
        assert abs(result - 0.4) < 0.001
