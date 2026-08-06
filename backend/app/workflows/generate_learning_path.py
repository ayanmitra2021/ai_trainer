"""generate_learning_path workflow — Step 2.8.

Orchestrates: Skill Profiler → Curriculum Planner → Item-Writer.

One workflow_runs row is written at the start; its status is updated to
completed or failed at the end. Each agent writes its own agent_runs row.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.base import ClaudeClient
from app.agents.curriculum_planner import CurriculumPlannerAgent
from app.agents.item_writer import ItemWriterAgent
from app.agents.skill_profiler import SkillProfilerAgent
from app.db.models import (
    Certification,
    LearningPath,
    LearningPathItem,
    PractitionerCertificationGoal,
    Skill,
    SkillProfileEvent,
    SkillProfileSnapshot,
    WorkflowRun,
)
from app.schemas.items import ItemWriterInput
from app.schemas.learning_paths import (
    CertGoalContext,
    CurriculumPlannerInput,
    GenerateLearningPathResponse,
    SkillProfilerInput,
    SkillScoreContext,
)


async def run_generate_learning_path(
    practitioner_id: str,
    db: AsyncSession,
    claude_client: ClaudeClient,
) -> GenerateLearningPathResponse:
    """Run the full generate_learning_path workflow.

    Sequence:
      1. Write workflow_runs row (status=running)
      2. Skill Profiler — compute / refresh skill snapshots
      3. Curriculum Planner — order the learning path
      4. Item-Writer — generate one starter item per path node
      5. Persist learning_path + learning_path_items
      6. Mark workflow_runs completed (or failed on any exception)
    """
    workflow_run_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    # ── 1. Open workflow run ───────────────────────────────────────────────
    workflow_run = WorkflowRun(
        id=workflow_run_id,
        workflow_name="generate_learning_path",
        triggered_by=practitioner_id,
        status="running",
        started_at=now,
    )
    db.add(workflow_run)
    await db.commit()

    try:
        result = await _run_steps(
            practitioner_id=practitioner_id,
            workflow_run_id=workflow_run_id,
            db=db,
            claude_client=claude_client,
        )
        workflow_run.status = "completed"
        workflow_run.completed_at = datetime.now(UTC)
        await db.commit()
        return result

    except Exception:
        workflow_run.status = "failed"
        workflow_run.completed_at = datetime.now(UTC)
        await db.commit()
        raise


async def _run_steps(
    practitioner_id: str,
    workflow_run_id: str,
    db: AsyncSession,
    claude_client: ClaudeClient,
) -> GenerateLearningPathResponse:
    # ── 2. Skill Profiler ─────────────────────────────────────────────────
    # Fetch raw events
    events_result = await db.execute(
        select(SkillProfileEvent)
        .where(SkillProfileEvent.practitioner_id == practitioner_id)
        .order_by(SkillProfileEvent.occurred_at.desc())
    )
    events = events_result.scalars().all()
    events_data = [
        {
            "skill_id": e.skill_id,
            "source": e.source,
            "signal_strength": float(e.signal_strength),
            "occurred_at": e.occurred_at.isoformat(),
            "metadata": e.metadata_,
        }
        for e in events
    ]

    profiler_input = SkillProfilerInput(
        practitioner_id=practitioner_id,
        events=events_data,
    )
    profiler = SkillProfilerAgent(
        client=claude_client, db_session=db, workflow_run_id=workflow_run_id
    )
    profiler_output = await profiler.run(profiler_input)

    # Upsert skill snapshots
    for score in profiler_output.skill_scores:
        existing = await db.get(
            SkillProfileSnapshot, (practitioner_id, score.skill_id)
        )
        if existing is not None:
            existing.mastery_score = score.mastery_score
            existing.confidence = score.confidence
            existing.last_computed_at = datetime.now(UTC)
        else:
            snapshot = SkillProfileSnapshot(
                practitioner_id=practitioner_id,
                skill_id=score.skill_id,
                mastery_score=score.mastery_score,
                confidence=score.confidence,
                last_computed_at=datetime.now(UTC),
            )
            db.add(snapshot)
    await db.flush()

    # ── 3. Curriculum Planner ──────────────────────────────────────────────
    # Build skill score context with names
    skill_scores_context: list[SkillScoreContext] = []
    for score in profiler_output.skill_scores:
        skill = await db.get(Skill, score.skill_id)
        skill_scores_context.append(
            SkillScoreContext(
                skill_id=score.skill_id,
                skill_name=skill.name if skill else score.skill_id,
                mastery_score=score.mastery_score,
                confidence=score.confidence,
            )
        )

    # Check for active certification goal
    cert_goal_context: CertGoalContext | None = None
    goal_result = await db.execute(
        select(PractitionerCertificationGoal)
        .options(
            selectinload(PractitionerCertificationGoal.certification).selectinload(
                Certification.certification_skills
            )
        )
        .where(
            PractitionerCertificationGoal.practitioner_id == practitioner_id,
            PractitionerCertificationGoal.status == "selected",
        )
        .order_by(PractitionerCertificationGoal.selected_at.desc())
        .limit(1)
    )
    active_goal = goal_result.scalar_one_or_none()
    if active_goal is not None:
        cert = active_goal.certification
        skill_weights = {
            cs.skill_id: float(cs.weight)
            for cs in cert.certification_skills
        }
        cert_goal_context = CertGoalContext(
            certification_code=cert.code,
            certification_name=cert.name,
            status=active_goal.status,
            skill_weights=skill_weights,
        )

    planner_input = CurriculumPlannerInput(
        practitioner_id=practitioner_id,
        skill_scores=skill_scores_context,
        certification_goal=cert_goal_context,
    )
    planner = CurriculumPlannerAgent(
        client=claude_client, db_session=db, workflow_run_id=workflow_run_id
    )
    planner_output = await planner.run(planner_input)

    # ── 4. Item-Writer (one starter item per path node) ───────────────────
    item_writer = ItemWriterAgent(
        client=claude_client, db_session=db, workflow_run_id=workflow_run_id
    )
    # We generate items in parallel-ish: run sequentially here for simplicity;
    # Phase 3 refactor can use asyncio.gather if latency matters.
    from app.db.models import Item as ItemModel

    items_by_skill: dict[str, str] = {}  # skill_id → item_id
    for path_item in planner_output.path_items:
        skill = await db.get(Skill, path_item.skill_id)
        if skill is None:
            continue  # skip if skill not found (shouldn't happen in practice)
        writer_input = ItemWriterInput(
            skill_id=path_item.skill_id,
            skill_name=skill.name,
            skill_description=skill.description,
            item_type="mcq",
            target_difficulty=0.4,  # starter difficulty — practitioners are new to the path
        )
        writer_output = await item_writer.run(writer_input)

        item_id = str(uuid.uuid4())
        item = ItemModel(
            id=item_id,
            skill_id=path_item.skill_id,
            item_type=writer_output.item_type,
            prompt=writer_output.prompt,
            # answer_key is now a typed Pydantic model; serialize to dict for JSONB storage.
            answer_key=writer_output.answer_key.model_dump(),
            trap_explanation=writer_output.trap_explanation,
            difficulty=writer_output.difficulty,
            calibration_stats={"attempt_count": 0, "total_score": 0.0, "trap_selection_count": 0},
        )
        db.add(item)
        items_by_skill[path_item.skill_id] = item_id

    await db.flush()

    # ── 5. Persist learning path ───────────────────────────────────────────
    learning_path_id = str(uuid.uuid4())
    learning_path = LearningPath(
        id=learning_path_id,
        practitioner_id=practitioner_id,
        generated_at=datetime.now(UTC),
        status="draft",
        workflow_run_id=workflow_run_id,
    )
    db.add(learning_path)
    await db.flush()

    for seq_order, path_item_spec in enumerate(planner_output.path_items):
        lp_item = LearningPathItem(
            id=str(uuid.uuid4()),
            learning_path_id=learning_path_id,
            skill_id=path_item_spec.skill_id,
            sequence_order=seq_order,
            resource_type=path_item_spec.resource_type,
            status="pending",
            rationale=path_item_spec.rationale,
        )
        db.add(lp_item)

    await db.flush()

    return GenerateLearningPathResponse(
        workflow_run_id=workflow_run_id,
        learning_path_id=learning_path_id,
        status="completed",
    )
