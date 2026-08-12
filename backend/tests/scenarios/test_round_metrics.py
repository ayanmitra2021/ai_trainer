"""Step 10.7 — Round-based mastery scoring utility scenarios.

Scenario 1: All generation-1 items answered with 100% → current_mastery_score ≤ 0.50
  (ceiling enforced: ceiling(1) = 1 - 0.5^1 = 0.5)

Scenario 2: Rounds 1 and 2 both 100% → current_mastery_score > 0.50 and ≤ 0.75
  (ceiling(2) = 1 - 0.5^2 = 0.75, weighted_accuracy = 1.0)

Scenario 3: Round 3 accuracy = 40% after good rounds 1 & 2 →
  current_mastery_score < score_after_round_2
  (recency weighting penalises the recent bad round)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.round_metrics import (
    compute_ceiling,
    compute_round_metrics,
    compute_weighted_accuracy,
)
from app.db.models import Attempt, Item, Practitioner, Skill


# ── helpers ───────────────────────────────────────────────────────────────────


async def _create_practitioner(db: AsyncSession) -> Practitioner:
    p = Practitioner(
        id=str(uuid.uuid4()),
        name="Round Metrics Test",
        email=f"round-metrics-{uuid.uuid4().hex[:6]}@test.com",
    )
    db.add(p)
    await db.flush()
    return p


async def _create_skill(db: AsyncSession) -> Skill:
    s = Skill(
        id=str(uuid.uuid4()),
        name="Round Test Skill",
        category="Testing",
    )
    db.add(s)
    await db.flush()
    return s


async def _create_items(
    db: AsyncSession, skill_id: str, count: int, generation: int = 1
) -> list[Item]:
    """Create `count` items for a skill at a given generation."""
    items = []
    for i in range(count):
        item = Item(
            id=str(uuid.uuid4()),
            skill_id=skill_id,
            item_type="mcq",
            prompt=f"Gen {generation} question {i + 1}",
            answer_key={"options": ["A", "B", "C", "D"], "correct_index": 0},
            difficulty=0.5,
            generation=generation,
        )
        db.add(item)
        items.append(item)
    await db.flush()
    return items


async def _attempt_items(
    db: AsyncSession,
    practitioner_id: str,
    items: list[Item],
    score: float,
    base_time: datetime | None = None,
) -> None:
    """Record one attempt per item with the given score."""
    if base_time is None:
        base_time = datetime.now(UTC)
    for i, item in enumerate(items):
        attempt = Attempt(
            id=str(uuid.uuid4()),
            practitioner_id=practitioner_id,
            item_id=item.id,
            response={"selected_index": 0},
            score=score,
            grader_rationale=f"Score {score}",
            attempted_at=base_time + timedelta(seconds=i),
        )
        db.add(attempt)
    await db.flush()


# ── Scenario 1: generation-1 at 100% → mastery ≤ 0.50 ────────────────────────


class TestRoundMetricsCeiling:
    async def test_all_gen1_correct_yields_mastery_at_most_0_50(
        self, db_session: AsyncSession
    ):
        """
        Scenario 1: All generation-1 items answered with 100% →
          current_mastery_score ≤ 0.50 (ceiling enforced).
          ceiling(1) = 1 - 0.5^1 = 0.5
          weighted_accuracy = 1.0
          mastery = 0.5 × 1.0 = 0.50
        """
        practitioner = await _create_practitioner(db_session)
        skill = await _create_skill(db_session)

        # Create 3 gen-1 items
        gen1_items = await _create_items(db_session, skill.id, 3, generation=1)

        # Attempt all with 100%
        await _attempt_items(db_session, practitioner.id, gen1_items, score=1.0)

        # Compute
        metrics = await compute_round_metrics(
            practitioner_id=practitioner.id,
            skill_id=skill.id,
            db=db_session,
        )

        assert metrics.rounds_completed == 1
        assert len(metrics.per_round_accuracy) == 1
        assert abs(metrics.per_round_accuracy[0] - 1.0) < 1e-9

        # ceiling(1) = 0.5
        assert abs(metrics.mastery_ceiling - 0.5) < 1e-9, (
            f"Expected ceiling=0.5 for 1 round, got {metrics.mastery_ceiling}"
        )

        # mastery = ceiling × weighted_accuracy = 0.5 × 1.0 = 0.5
        assert metrics.current_mastery_score <= 0.50 + 1e-9, (
            f"Expected mastery_score ≤ 0.50, got {metrics.current_mastery_score}"
        )

    def test_compute_ceiling_formula(self):
        """Unit test for the ceiling formula."""
        assert compute_ceiling(0) == 0.0
        assert abs(compute_ceiling(1) - 0.5) < 1e-9
        assert abs(compute_ceiling(2) - 0.75) < 1e-9
        assert abs(compute_ceiling(3) - 0.875) < 1e-9


# ── Scenario 2: gen1 + gen2 at 100% → 0.50 < mastery ≤ 0.75 ─────────────────


class TestRoundMetricsTwoRounds:
    async def test_two_perfect_rounds_yield_mastery_between_0_50_and_0_75(
        self, db_session: AsyncSession
    ):
        """
        Scenario 2: Rounds 1 and 2 both 100% →
          current_mastery_score > 0.50 and ≤ 0.75.
          ceiling(2) = 0.75
          weighted_accuracy(1.0, 1.0) = 1.0
          mastery = 0.75 × 1.0 = 0.75
        """
        practitioner = await _create_practitioner(db_session)
        skill = await _create_skill(db_session)

        gen1 = await _create_items(db_session, skill.id, 2, generation=1)
        gen2 = await _create_items(db_session, skill.id, 2, generation=2)

        t0 = datetime.now(UTC)
        await _attempt_items(db_session, practitioner.id, gen1, score=1.0, base_time=t0)
        await _attempt_items(
            db_session, practitioner.id, gen2, score=1.0,
            base_time=t0 + timedelta(days=1)
        )

        metrics = await compute_round_metrics(
            practitioner_id=practitioner.id,
            skill_id=skill.id,
            db=db_session,
        )

        assert metrics.rounds_completed == 2
        assert metrics.current_mastery_score > 0.50, (
            f"After 2 perfect rounds, mastery should exceed 0.50, got {metrics.current_mastery_score}"
        )
        assert metrics.current_mastery_score <= 0.75 + 1e-9, (
            f"After 2 rounds, mastery ≤ 0.75 (ceiling(2)), got {metrics.current_mastery_score}"
        )

    def test_compute_weighted_accuracy_two_perfect_rounds(self):
        """Unit test for the weighted accuracy formula with two 1.0 rounds."""
        # weights: round1=2^0=1, round2=2^1=2 → total=3
        # weighted = (1.0*1 + 1.0*2) / 3 = 1.0
        result = compute_weighted_accuracy([1.0, 1.0])
        assert abs(result - 1.0) < 1e-9


# ── Scenario 3: bad round 3 pulls score below round-2 score ──────────────────


class TestRoundMetricsDecline:
    async def test_bad_round_3_reduces_mastery_below_round_2_score(
        self, db_session: AsyncSession
    ):
        """
        Scenario 3: Round 3 accuracy = 40% after good rounds 1 & 2 →
          current_mastery_score < score_after_round_2.
          round weights: r1=1, r2=2, r3=4 → total=7
          weighted_accuracy = (1.0*1 + 1.0*2 + 0.4*4) / 7 = (1+2+1.6)/7 = 4.6/7 ≈ 0.657
          ceiling(3) = 0.875
          mastery = 0.875 * 0.657 ≈ 0.575
          After round 2: ceiling(2)=0.75, wa=1.0 → mastery=0.75
          0.575 < 0.75 ✓
        """
        practitioner = await _create_practitioner(db_session)
        skill = await _create_skill(db_session)

        gen1 = await _create_items(db_session, skill.id, 2, generation=1)
        gen2 = await _create_items(db_session, skill.id, 2, generation=2)
        gen3 = await _create_items(db_session, skill.id, 2, generation=3)

        t0 = datetime.now(UTC)
        await _attempt_items(db_session, practitioner.id, gen1, score=1.0, base_time=t0)
        await _attempt_items(
            db_session, practitioner.id, gen2, score=1.0,
            base_time=t0 + timedelta(days=1)
        )
        # Bad round 3: 40% accuracy
        await _attempt_items(
            db_session, practitioner.id, gen3, score=0.4,
            base_time=t0 + timedelta(days=2)
        )

        metrics = await compute_round_metrics(
            practitioner_id=practitioner.id,
            skill_id=skill.id,
            db=db_session,
        )

        assert metrics.rounds_completed == 3, (
            f"Expected 3 completed rounds, got {metrics.rounds_completed}"
        )

        # Score after round 2 would have been 0.75
        score_after_round_2 = 0.75
        assert metrics.current_mastery_score < score_after_round_2, (
            f"Bad round 3 should reduce mastery below {score_after_round_2}, "
            f"got {metrics.current_mastery_score}"
        )

    def test_weighted_accuracy_bad_third_round(self):
        """Unit test: bad third round reduces weighted accuracy significantly."""
        # r1=1.0, r2=1.0, r3=0.4; weights 1,2,4
        wa = compute_weighted_accuracy([1.0, 1.0, 0.4])
        # (1.0*1 + 1.0*2 + 0.4*4) / 7 = (1 + 2 + 1.6) / 7 = 4.6/7
        expected = 4.6 / 7
        assert abs(wa - expected) < 1e-6, f"Expected {expected}, got {wa}"

    async def test_incomplete_round_is_not_counted(self, db_session: AsyncSession):
        """Items in gen-2 that are not all attempted means only gen-1 is counted."""
        practitioner = await _create_practitioner(db_session)
        skill = await _create_skill(db_session)

        gen1 = await _create_items(db_session, skill.id, 2, generation=1)
        gen2 = await _create_items(db_session, skill.id, 2, generation=2)

        # Attempt all gen-1
        await _attempt_items(db_session, practitioner.id, gen1, score=1.0)
        # Only attempt ONE of the two gen-2 items (incomplete round)
        t0 = datetime.now(UTC)
        incomplete_attempt = Attempt(
            id=str(uuid.uuid4()),
            practitioner_id=practitioner.id,
            item_id=gen2[0].id,
            response={"selected_index": 0},
            score=1.0,
            grader_rationale="One of two",
            attempted_at=t0 + timedelta(days=1),
        )
        db_session.add(incomplete_attempt)
        await db_session.flush()

        metrics = await compute_round_metrics(
            practitioner_id=practitioner.id,
            skill_id=skill.id,
            db=db_session,
        )

        # Only gen-1 should count (gen-2 is incomplete)
        assert metrics.rounds_completed == 1, (
            f"Incomplete gen-2 should not count; expected rounds=1, got {metrics.rounds_completed}"
        )
        assert abs(metrics.mastery_ceiling - 0.5) < 1e-9
