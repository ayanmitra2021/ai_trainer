"""Step 3.4 — Rollup Reporter Agent scenarios.

Scenario: A cohort at/above the minimum size produces a rollup with populated metrics.
Scenario: A cohort below the minimum size is refused, not silently shown.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.rollup_reporter import MINIMUM_COHORT_SIZE, RollupReporterAgent
from app.schemas.pulse import PractitionerCorrelationSummary, RollupReporterInput
from tests.fixtures.stub_claude_client import StubClaudeClient


def _summary(trained: float = 0.7, adopted: float = 0.5, gap: float = 0.2, gaps: int = 1) -> PractitionerCorrelationSummary:
    return PractitionerCorrelationSummary(
        trained_skills_count=3,
        skills_with_gap_count=gaps,
        avg_trained_score=trained,
        avg_adoption_score=adopted,
        avg_gap_score=gap,
    )


class TestRollupReporterScenarios:
    async def test_cohort_at_minimum_produces_populated_rollup(
        self, db_session: AsyncSession
    ):
        """
        Scenario: A cohort at/above the minimum size produces a rollup with populated metrics.
          Given a cohort of exactly MINIMUM_COHORT_SIZE practitioners
          When the Rollup Reporter Agent runs
          Then min_cohort_size_met is True
          And metrics and narrative are populated
        """
        # Given — build exactly MINIMUM_COHORT_SIZE summaries
        practitioner_count = MINIMUM_COHORT_SIZE
        summaries = [_summary() for _ in range(practitioner_count)]

        stub_client = StubClaudeClient(
            response_data={
                "min_cohort_size_met": True,
                "metrics": {
                    "avg_gap_score": 0.2,
                    "pct_with_adoption_gap": 0.4,
                    "top_gap_skill_names": ["Prompt Engineering"],
                    "adoption_trend": "stable",
                },
                "narrative": (
                    f"Across {practitioner_count} practitioners this week, the majority are actively "
                    "applying trained skills. Prompt Engineering shows the widest gap — consider "
                    "introducing project sprints to close it. Overall adoption is stable."
                ),
                "reasoning": f"Cohort of {practitioner_count} meets the minimum of {MINIMUM_COHORT_SIZE}.",
            }
        )

        agent_input = RollupReporterInput(
            scope="practice",
            scope_ref="AI & Engineering",
            period_start="2026-07-01",
            period_end="2026-07-31",
            practitioner_count=practitioner_count,
            practitioner_summaries=summaries,
            min_cohort_size=MINIMUM_COHORT_SIZE,
        )

        # When
        agent = RollupReporterAgent(client=stub_client, db_session=db_session)
        result = await agent.run(agent_input)

        # Then
        assert result.min_cohort_size_met is True
        assert result.metrics is not None
        assert result.narrative is not None
        assert len(result.narrative) > 0

    async def test_cohort_below_minimum_is_withheld_not_shown(
        self, db_session: AsyncSession
    ):
        """
        Scenario: A cohort below the minimum size is refused, not silently shown.
          Given a cohort smaller than MINIMUM_COHORT_SIZE
          When the Rollup Reporter Agent runs
          Then min_cohort_size_met is False
          And metrics and narrative are None (structural privacy gate)
        """
        # Given — one fewer than the minimum
        small_count = max(1, MINIMUM_COHORT_SIZE - 1)
        summaries = [_summary() for _ in range(small_count)]

        stub_client = StubClaudeClient(
            response_data={
                "min_cohort_size_met": False,
                "metrics": None,
                "narrative": None,
                "reasoning": (
                    f"Cohort of {small_count} is below the minimum threshold of {MINIMUM_COHORT_SIZE} "
                    "— no aggregate data produced to protect individual privacy."
                ),
            }
        )

        agent_input = RollupReporterInput(
            scope="team",
            scope_ref="Alpha Team",
            period_start="2026-07-01",
            period_end="2026-07-31",
            practitioner_count=small_count,
            practitioner_summaries=summaries,
            min_cohort_size=MINIMUM_COHORT_SIZE,
        )

        # When
        agent = RollupReporterAgent(client=stub_client, db_session=db_session)
        result = await agent.run(agent_input)

        # Then — privacy gate holds
        assert result.min_cohort_size_met is False
        assert result.metrics is None, (
            "metrics must be None when cohort is below minimum — "
            "this is a structural privacy commitment, not a display choice"
        )
        assert result.narrative is None, (
            "narrative must be None when cohort is below minimum"
        )
        # reasoning must explain the refusal
        assert result.reasoning
        assert str(small_count) in result.reasoning or "threshold" in result.reasoning.lower()
