"""Step 3.5 — Nightly Pulse orchestrator workflow scenarios.

Scenario: A full nightly run across multiple practitioners completes with one
          workflow_runs row and all four steps executed per practitioner.
Scenario: One practitioner's failure doesn't abort the whole run.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.rollup_reporter import MINIMUM_COHORT_SIZE
from app.db.models import (
    AgentRun,
    CorrelationSnapshot,
    Nudge,
    Practitioner,
    Rollup,
    Skill,
    SkillProfileSnapshot,
    WorkflowRun,
)
from app.workflows.nightly_pulse import run_nightly_pulse
from tests.fixtures.stub_claude_client import StubClaudeClient


# ── Shared fixtures ────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def skill(db_session: AsyncSession) -> Skill:
    s = Skill(
        id=str(uuid.uuid4()),
        name="Prompt Engineering",
        category="AI Foundations",
        description="Crafting effective prompts.",
    )
    db_session.add(s)
    await db_session.flush()
    return s


@pytest_asyncio.fixture
async def practitioners_with_snapshots(
    db_session: AsyncSession, skill: Skill
):
    """Create MINIMUM_COHORT_SIZE practitioners each with a skill snapshot."""
    practitioners = []
    for i in range(MINIMUM_COHORT_SIZE):
        p = Practitioner(
            id=str(uuid.uuid4()),
            name=f"Pulse Test {i}",
            email=f"pulse.test.{i}@mastery.example",
        )
        db_session.add(p)
        await db_session.flush()

        snap = SkillProfileSnapshot(
            practitioner_id=p.id,
            skill_id=skill.id,
            mastery_score=0.75,
            confidence=0.8,
            last_computed_at=datetime.now(UTC) - timedelta(days=7),
        )
        db_session.add(snap)
        practitioners.append(p)

    await db_session.flush()
    return practitioners


def _make_stub_client_for_full_pulse(skill_id: str, practitioner_count: int) -> StubClaudeClient:
    """Stub covering usage_signal + correlation + nudge_composer (per practitioner) + rollup_reporter."""
    # The usage_signal agent will be called once per practitioner (even with empty signals)
    usage_response = {
        "normalized_events": [],
        "unmapped_count": 0,
        "summary": "No signals this period.",
    }
    # Correlation — high mastery, no usage → gap
    corr_response = {
        "skill_correlations": [
            {
                "skill_id": skill_id,
                "trained_score": 0.75,
                "adoption_score": 0.05,
                "gap_score": 0.70,
                "has_adoption_gap": True,
                "reasoning": "High mastery, zero usage in 30 days — gap flagged (correlation, not causation).",
            }
        ],
        "summary": "1 skill with adoption gap (correlation, not causation).",
    }
    # Nudge composer — draft a nudge
    nudge_response = {
        "should_compose": True,
        "nudge_type": "gap_alert",
        "content": "You've built solid foundations in Prompt Engineering — would a small project applying it be useful?",
        "reasoning": "Gap score 0.70 warrants a nudge.",
    }
    # Rollup reporter — called once at the end
    rollup_response = {
        "min_cohort_size_met": True,
        "metrics": {
            "avg_gap_score": 0.70,
            "pct_with_adoption_gap": 1.0,
            "top_gap_skill_names": ["Prompt Engineering"],
            "adoption_trend": "stable",
        },
        "narrative": "All practitioners show a Prompt Engineering gap — consider a project sprint.",
        "reasoning": f"Cohort of {practitioner_count} meets the threshold.",
    }

    # side_effects order: per practitioner (usage + corr + nudge) × N, then rollup
    side_effects = []
    for _ in range(practitioner_count):
        side_effects.extend([usage_response, corr_response, nudge_response])
    side_effects.append(rollup_response)

    return StubClaudeClient(side_effects=side_effects)


class TestNightlyPulseWorkflow:
    async def test_full_run_creates_workflow_and_agent_rows(
        self,
        db_session: AsyncSession,
        practitioners_with_snapshots,
        skill: Skill,
    ):
        """
        Scenario: A full nightly run across multiple practitioners completes with one
          workflow_runs row and all four agent types executed.
          Given MINIMUM_COHORT_SIZE practitioners each with a skill snapshot
          When the nightly_pulse workflow runs
          Then a workflow_runs row with status 'completed' exists
          And correlation_snapshots are written for each practitioner
          And nudges are drafted for each practitioner (gap present)
          And a rollup row exists
        """
        # Given
        practitioners = practitioners_with_snapshots
        practitioner_ids = [p.id for p in practitioners]
        stub_client = _make_stub_client_for_full_pulse(skill.id, len(practitioners))

        # When
        result = await run_nightly_pulse(
            practitioner_ids=practitioner_ids,
            scope="practice",
            scope_ref="Test Practice",
            period_start=datetime.now(UTC) - timedelta(days=7),
            period_end=datetime.now(UTC),
            db=db_session,
            claude_client=stub_client,
            raw_signals_by_practitioner={},  # empty — no MCP signals in tests
        )

        # Then — workflow completed
        wf_result = await db_session.execute(
            select(WorkflowRun).where(WorkflowRun.id == result.workflow_run_id)
        )
        workflow_run = wf_result.scalar_one_or_none()
        assert workflow_run is not None
        assert workflow_run.status == "completed"

        # And — correlation snapshots exist per practitioner
        for pid in practitioner_ids:
            snap_result = await db_session.execute(
                select(CorrelationSnapshot).where(CorrelationSnapshot.practitioner_id == pid)
            )
            snaps = snap_result.scalars().all()
            assert len(snaps) >= 1, f"Expected correlation snapshot for practitioner {pid}"

        # And — nudges drafted (one per practitioner with gap)
        for pid in practitioner_ids:
            nudge_result = await db_session.execute(
                select(Nudge).where(Nudge.practitioner_id == pid)
            )
            nudges = nudge_result.scalars().all()
            assert len(nudges) >= 1, f"Expected a drafted nudge for practitioner {pid}"
            assert nudges[0].status == "drafted"

        # And — rollup written
        assert result.rollup_id is not None
        rollup_result = await db_session.execute(
            select(Rollup).where(Rollup.id == result.rollup_id)
        )
        rollup = rollup_result.scalar_one_or_none()
        assert rollup is not None
        assert rollup.min_cohort_size_met is True

    async def test_one_practitioner_failure_does_not_abort_run(
        self,
        db_session: AsyncSession,
        practitioners_with_snapshots,
        skill: Skill,
    ):
        """
        Scenario: One practitioner's failure doesn't abort the whole run.
          Given N practitioners
          And the first practitioner's usage_signal step is forced to fail
          When the nightly_pulse workflow runs
          Then the workflow completes with status 'partial'
          And the remaining practitioners still have correlation snapshots
        """
        # Given
        practitioners = practitioners_with_snapshots
        practitioner_ids = [p.id for p in practitioners]

        # Build side_effects: first practitioner fails on usage_signal,
        # remaining practitioners succeed
        failing_error = ValueError("Simulated usage-signal failure for practitioner 0")

        good_usage = {"normalized_events": [], "unmapped_count": 0, "summary": "No signals."}
        good_corr = {
            "skill_correlations": [
                {
                    "skill_id": skill.id,
                    "trained_score": 0.75,
                    "adoption_score": 0.05,
                    "gap_score": 0.70,
                    "has_adoption_gap": True,
                    "reasoning": "High mastery, low usage — gap flagged (correlation, not causation).",
                }
            ],
            "summary": "1 gap (correlation, not causation).",
        }
        good_nudge = {
            "should_compose": True,
            "nudge_type": "gap_alert",
            "content": "You've built solid foundations — consider applying your skills in a project.",
            "reasoning": "Gap score warrants a nudge.",
        }
        good_rollup = {
            "min_cohort_size_met": True,
            "metrics": {
                "avg_gap_score": 0.60,
                "pct_with_adoption_gap": 0.8,
                "top_gap_skill_names": ["Prompt Engineering"],
                "adoption_trend": "stable",
            },
            "narrative": "Most practitioners show adoption gaps — consider a project sprint.",
            "reasoning": "Cohort meets threshold.",
        }

        # First practitioner: fails at usage_signal
        # Remaining practitioners: succeed (usage + corr + nudge each)
        side_effects: list = [failing_error]
        for _ in range(len(practitioner_ids) - 1):
            side_effects.extend([good_usage, good_corr, good_nudge])
        side_effects.append(good_rollup)

        stub_client = StubClaudeClient(side_effects=side_effects)

        # When
        result = await run_nightly_pulse(
            practitioner_ids=practitioner_ids,
            scope="practice",
            scope_ref="Test Practice",
            period_start=datetime.now(UTC) - timedelta(days=7),
            period_end=datetime.now(UTC),
            db=db_session,
            claude_client=stub_client,
            raw_signals_by_practitioner={},
        )

        # Then — workflow is 'partial', not 'failed'
        assert result.status == "partial", (
            f"Expected 'partial' status when one practitioner fails, got {result.status!r}"
        )

        # And — the failing practitioner is reported as error
        error_results = [r for r in result.practitioner_results if r.status == "error"]
        assert len(error_results) == 1
        assert error_results[0].practitioner_id == practitioner_ids[0]

        # And — the remaining practitioners have correlation snapshots
        for pid in practitioner_ids[1:]:
            snap_result = await db_session.execute(
                select(CorrelationSnapshot).where(CorrelationSnapshot.practitioner_id == pid)
            )
            snaps = snap_result.scalars().all()
            assert len(snaps) >= 1, (
                f"Practitioner {pid} should have correlation snapshots even though another failed"
            )
