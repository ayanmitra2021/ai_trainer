"""Step 3.2 — Correlation Agent scenarios.

Scenario: High mastery with no recent usage produces a visible gap.
Scenario: High mastery with regular usage produces a near-zero gap.
Scenario: Low mastery is not reported as an adoption gap.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.correlation import CorrelationAgent
from app.schemas.pulse import (
    CorrelationInput,
    SkillSnapshotContext,
    SkillUsageSummary,
)
from tests.fixtures.stub_claude_client import StubClaudeClient


def _snapshot(skill_id: str, mastery: float, confidence: float = 0.8) -> SkillSnapshotContext:
    return SkillSnapshotContext(
        skill_id=skill_id,
        skill_name="Test Skill",
        mastery_score=mastery,
        confidence=confidence,
        last_computed_at=(datetime.now(UTC) - timedelta(days=7)).isoformat(),
    )


def _usage(skill_id: str, count_30d: int, count_90d: int, most_recent_days_ago: int | None) -> SkillUsageSummary:
    return SkillUsageSummary(
        skill_id=skill_id,
        skill_name="Test Skill",
        event_count_30d=count_30d,
        event_count_90d=count_90d,
        most_recent_at=(
            (datetime.now(UTC) - timedelta(days=most_recent_days_ago)).isoformat()
            if most_recent_days_ago is not None
            else None
        ),
    )


class TestCorrelationScenarios:
    async def test_high_mastery_no_usage_produces_visible_gap(
        self, db_session: AsyncSession
    ):
        """
        Scenario: High mastery with no recent usage produces a visible gap.
          Given a high snapshot score (0.8) for a skill
            and no usage_events in the last 30+ days
          When the Correlation Agent runs
          Then gap_score is materially above zero
          And has_adoption_gap is True
        """
        # Given
        practitioner_id = str(uuid.uuid4())
        skill_id = str(uuid.uuid4())

        stub_client = StubClaudeClient(
            response_data={
                "skill_correlations": [
                    {
                        "skill_id": skill_id,
                        "trained_score": 0.80,
                        "adoption_score": 0.05,
                        "gap_score": 0.75,
                        "has_adoption_gap": True,
                        "reasoning": (
                            "Mastery score 0.80 from certification signals; 0 usage events in 30 days, "
                            "last event 47 days ago. Gap flagged — but low usage could reflect project "
                            "rotation rather than non-adoption (correlation, not causation)."
                        ),
                    }
                ],
                "summary": (
                    "1 skill assessed; 1 potential adoption gap (correlation, not causation — "
                    "usage evidence is a proxy, not a direct measure of applied skill)."
                ),
            }
        )

        agent_input = CorrelationInput(
            practitioner_id=practitioner_id,
            skill_snapshots=[_snapshot(skill_id, mastery=0.80)],
            skill_usage_summaries=[_usage(skill_id, count_30d=0, count_90d=1, most_recent_days_ago=47)],
        )

        # When
        agent = CorrelationAgent(client=stub_client, db_session=db_session)
        result = await agent.run(agent_input)

        # Then
        assert len(result.skill_correlations) >= 1
        corr = next(c for c in result.skill_correlations if c.skill_id == skill_id)
        assert corr.gap_score > 0.3, f"Expected gap_score > 0.3, got {corr.gap_score}"
        assert corr.has_adoption_gap is True

    async def test_high_mastery_regular_usage_produces_near_zero_gap(
        self, db_session: AsyncSession
    ):
        """
        Scenario: High mastery with regular usage produces a near-zero gap.
          Given the same high mastery score
            and frequent usage events (8 in the last 30 days)
          When the Correlation Agent runs
          Then gap_score is near zero
          And has_adoption_gap is False
        """
        # Given
        practitioner_id = str(uuid.uuid4())
        skill_id = str(uuid.uuid4())

        stub_client = StubClaudeClient(
            response_data={
                "skill_correlations": [
                    {
                        "skill_id": skill_id,
                        "trained_score": 0.80,
                        "adoption_score": 0.82,
                        "gap_score": 0.0,
                        "has_adoption_gap": False,
                        "reasoning": (
                            "Mastery 0.80; 8 usage events in 30 days, most recent 2 days ago. "
                            "Adoption evidence is strong — no gap."
                        ),
                    }
                ],
                "summary": (
                    "1 skill assessed; 0 adoption gaps (correlation, not causation). "
                    "Practitioner is actively applying trained skill."
                ),
            }
        )

        agent_input = CorrelationInput(
            practitioner_id=practitioner_id,
            skill_snapshots=[_snapshot(skill_id, mastery=0.80)],
            skill_usage_summaries=[_usage(skill_id, count_30d=8, count_90d=24, most_recent_days_ago=2)],
        )

        # When
        agent = CorrelationAgent(client=stub_client, db_session=db_session)
        result = await agent.run(agent_input)

        # Then
        corr = next(c for c in result.skill_correlations if c.skill_id == skill_id)
        assert corr.gap_score < 0.3, f"Expected near-zero gap, got {corr.gap_score}"
        assert corr.has_adoption_gap is False

    async def test_low_mastery_is_not_reported_as_adoption_gap(
        self, db_session: AsyncSession
    ):
        """
        Scenario: Low mastery is not reported as an adoption gap.
          Given a low mastery score (0.3) — below the 0.5 training threshold
            and no usage events (which is expected for a skill not yet learned)
          When the Correlation Agent runs
          Then has_adoption_gap is False
          And gap_score reflects that this is a training need, not an adoption problem
        """
        # Given
        practitioner_id = str(uuid.uuid4())
        skill_id = str(uuid.uuid4())

        stub_client = StubClaudeClient(
            response_data={
                "skill_correlations": [
                    {
                        "skill_id": skill_id,
                        "trained_score": 0.30,
                        "adoption_score": 0.05,
                        "gap_score": 0.0,  # forced to 0.0 — low mastery is a training need
                        "has_adoption_gap": False,
                        "reasoning": (
                            "Mastery score 0.30 is below the 0.5 threshold. "
                            "Low usage alongside low mastery is expected — this is a training need, "
                            "not an adoption gap. No gap flagged."
                        ),
                    }
                ],
                "summary": (
                    "1 skill assessed; 0 adoption gaps (correlation, not causation). "
                    "1 skill has low mastery and is excluded from gap analysis — treat as training need."
                ),
            }
        )

        agent_input = CorrelationInput(
            practitioner_id=practitioner_id,
            skill_snapshots=[_snapshot(skill_id, mastery=0.30, confidence=0.5)],
            skill_usage_summaries=[_usage(skill_id, count_30d=0, count_90d=0, most_recent_days_ago=None)],
        )

        # When
        agent = CorrelationAgent(client=stub_client, db_session=db_session)
        result = await agent.run(agent_input)

        # Then — low mastery must not be flagged as an adoption gap
        corr = next(c for c in result.skill_correlations if c.skill_id == skill_id)
        assert corr.has_adoption_gap is False, (
            "Low mastery should never be flagged as an adoption gap — it's a training need"
        )
        # The gap_score should be 0 for low-mastery skills regardless of usage
        assert corr.gap_score == 0.0, (
            f"Expected gap_score=0.0 for low-mastery skill, got {corr.gap_score}"
        )
