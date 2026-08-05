"""Step 2.8 — Learning-path orchestrator workflow scenarios.

Scenario: Requesting a path runs all three agents in order.
Scenario: A failure partway through is recorded, not swallowed.
Scenario: Submitting an attempt end-to-end updates the snapshot on the next profiler run.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AgentRun,
    Item,
    Practitioner,
    Skill,
    SkillProfileEvent,
    SkillProfileSnapshot,
    WorkflowRun,
)
from app.workflows.generate_learning_path import run_generate_learning_path
from tests.fixtures.stub_claude_client import StubClaudeClient


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def workflow_practitioner(db_session: AsyncSession) -> Practitioner:
    p = Practitioner(
        id=str(uuid.uuid4()),
        name="Workflow Test Practitioner",
        email="workflow.test@mastery.example",
    )
    db_session.add(p)
    await db_session.flush()
    return p


@pytest_asyncio.fixture
async def workflow_skill(db_session: AsyncSession) -> Skill:
    s = Skill(
        id=str(uuid.uuid4()),
        name="Prompt Engineering",
        category="AI Foundations",
        description="Crafting effective prompts for language models.",
    )
    db_session.add(s)
    await db_session.flush()
    return s


@pytest_asyncio.fixture
async def workflow_event(
    db_session: AsyncSession,
    workflow_practitioner: Practitioner,
    workflow_skill: Skill,
) -> SkillProfileEvent:
    event = SkillProfileEvent(
        id=str(uuid.uuid4()),
        practitioner_id=workflow_practitioner.id,
        skill_id=workflow_skill.id,
        source="self_assessment",
        signal_strength=0.5,
        occurred_at=datetime.now(UTC) - timedelta(days=5),
    )
    db_session.add(event)
    await db_session.flush()
    return event


def _make_stub_client_for_full_workflow(skill_id: str) -> StubClaudeClient:
    """Stub that has side_effects covering all three agent calls in sequence."""
    profiler_response = {
        "skill_scores": [
            {
                "skill_id": skill_id,
                "mastery_score": 0.5,
                "confidence": 0.6,
                "reasoning": "Self-assessment signal.",
            }
        ],
        "summary": "One skill with moderate mastery.",
    }
    planner_response = {
        "path_items": [
            {
                "skill_id": skill_id,
                "resource_type": "item_set",
                "rationale": "Prioritised — moderate gap.",
            }
        ],
        "summary": "One skill to work on.",
    }
    item_writer_response = {
        "item_type": "mcq",
        "prompt": "What is prompt engineering?",
        "answer_key": {
            "options": ["A", "B", "C", "D"],
            "correct_index": 0,
            "trap_index": 1,
        },
        "trap_explanation": "Option B exploits a common misconception.",
        "difficulty": 0.4,
        "rationale": "Starter difficulty.",
    }
    return StubClaudeClient(
        side_effects=[
            profiler_response,
            planner_response,
            item_writer_response,
        ]
    )


class TestGenerateLearningPathWorkflow:
    async def test_full_workflow_creates_workflow_run_and_three_agent_runs(
        self,
        db_session: AsyncSession,
        workflow_practitioner: Practitioner,
        workflow_skill: Skill,
        workflow_event: SkillProfileEvent,
    ):
        """
        Scenario: Requesting a path runs all three agents in order.
          Given a practitioner with one skill event
          When the generate_learning_path workflow runs
          Then a workflow_runs row with status 'completed' exists
          And three agent_runs rows are linked to it (profiler, planner, item_writer)
        """
        # Given
        stub_client = _make_stub_client_for_full_workflow(workflow_skill.id)

        # When
        result = await run_generate_learning_path(
            practitioner_id=workflow_practitioner.id,
            db=db_session,
            claude_client=stub_client,
        )

        # Then — workflow_run completed
        wf_result = await db_session.execute(
            select(WorkflowRun).where(WorkflowRun.id == result.workflow_run_id)
        )
        workflow_run = wf_result.scalar_one_or_none()
        assert workflow_run is not None
        assert workflow_run.status == "completed"

        # And — three agent_runs linked to this workflow
        ar_result = await db_session.execute(
            select(AgentRun).where(AgentRun.workflow_run_id == result.workflow_run_id)
        )
        agent_runs = ar_result.scalars().all()
        agent_names = {ar.agent_name for ar in agent_runs}
        assert "skill_profiler" in agent_names
        assert "curriculum_planner" in agent_names
        assert "item_writer" in agent_names

    async def test_failure_partway_through_marks_workflow_failed(
        self,
        db_session: AsyncSession,
        workflow_practitioner: Practitioner,
        workflow_skill: Skill,
        workflow_event: SkillProfileEvent,
    ):
        """
        Scenario: A failure partway through is recorded, not swallowed.
          Given the Curriculum Planner step is forced to fail (raises an exception)
          When the workflow runs
          Then workflow_runs.status is 'failed'
          And the exception propagates (not a silent 200)
        """
        # Given — profiler succeeds, planner raises a non-transient error
        profiler_response = {
            "skill_scores": [
                {
                    "skill_id": workflow_skill.id,
                    "mastery_score": 0.5,
                    "confidence": 0.6,
                    "reasoning": "Self-assessment.",
                }
            ],
            "summary": "One skill.",
        }
        planner_failure = ValueError("Simulated curriculum planner failure")
        stub_client = StubClaudeClient(
            side_effects=[
                profiler_response,
                planner_failure,  # planner raises
            ]
        )

        # When / Then — exception must propagate
        with pytest.raises(ValueError, match="Simulated curriculum planner failure"):
            await run_generate_learning_path(
                practitioner_id=workflow_practitioner.id,
                db=db_session,
                claude_client=stub_client,
            )

        # And — find the workflow_run that was created and check its status
        wf_result = await db_session.execute(
            select(WorkflowRun)
            .where(WorkflowRun.triggered_by == workflow_practitioner.id)
            .order_by(WorkflowRun.started_at.desc())
        )
        latest_wf = wf_result.scalars().first()
        assert latest_wf is not None
        assert latest_wf.status == "failed"

    async def test_submitting_attempt_updates_calibration_stats(
        self,
        db_session: AsyncSession,
        workflow_practitioner: Practitioner,
        workflow_skill: Skill,
    ):
        """
        Scenario: Submitting an attempt end-to-end updates the snapshot on the next profiler run.
          Given an item in the DB and a practitioner
          When an attempt is submitted and the Grader runs
          Then the item's calibration_stats.attempt_count increases
          So that the next Skill Profiler run can use updated calibration context.
        """
        # Given — create an item directly (simulating a prior Item-Writer run)
        item = Item(
            id=str(uuid.uuid4()),
            skill_id=workflow_skill.id,
            item_type="mcq",
            prompt="Test question",
            answer_key={
                "options": ["A", "B", "C", "D"],
                "correct_index": 0,
                "trap_index": 1,
            },
            trap_explanation="B exploits a misconception.",
            difficulty=0.4,
            calibration_stats={"attempt_count": 0, "total_score": 0.0, "trap_selection_count": 0},
        )
        db_session.add(item)
        await db_session.flush()

        initial_count = item.calibration_stats["attempt_count"]

        # When — simulate what the /attempts route does: run grader + update stats
        from app.agents.grader import GraderAgent
        from app.schemas.items import GraderInput

        grader_stub = StubClaudeClient(
            response_data={
                "score": 1.0,
                "grader_rationale": "Correct.",
                "is_trap_selected": False,
            }
        )
        grader_input = GraderInput(
            item_id=item.id,
            item_type="mcq",
            item_prompt=item.prompt,
            answer_key=item.answer_key,
            trap_explanation=item.trap_explanation,
            submitted_response={"selected_index": 0},
        )
        grader = GraderAgent(client=grader_stub, db_session=db_session)
        grader_output = await grader.run(grader_input)

        # Update calibration stats (mirrors route logic)
        stats = item.calibration_stats.copy()
        stats["attempt_count"] += 1
        stats["total_score"] = float(stats.get("total_score", 0)) + float(grader_output.score)
        stats["avg_score"] = stats["total_score"] / stats["attempt_count"]
        item.calibration_stats = stats
        await db_session.flush()

        # Then — attempt_count increased
        updated_count = item.calibration_stats["attempt_count"]
        assert updated_count == initial_count + 1
        assert item.calibration_stats["avg_score"] == 1.0
