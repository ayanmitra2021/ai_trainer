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

from app.agents.base import ModelClient
from app.agents.curriculum_planner import CurriculumPlannerAgent
from app.agents.item_writer import ItemWriterAgent
from app.agents.model_client import create_model_client
from app.agents.skill_profiler import SkillProfilerAgent
from app.db.models import (
    Certification,
    LearningPath,
    LearningPathItem,
    MasteryHistory,
    Practitioner,
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
    claude_client: ModelClient | None = None,
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
    # Create model client if not provided (for backward compatibility in tests)
    if claude_client is None:
        claude_client = create_model_client()
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

    # Validate practitioner exists before proceeding
    practitioner = await db.get(Practitioner, practitioner_id)
    if practitioner is None:
        workflow_run.status = "failed"
        workflow_run.completed_at = datetime.now(UTC)
        await db.commit()
        raise ValueError(f"Practitioner {practitioner_id} not found")

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
    claude_client: ModelClient,
) -> GenerateLearningPathResponse:
    # ── 2. Skill Profiler ─────────────────────────────────────────────────
    # Phase 9.4: fetch ONLY quiz_attempt events. Self-assessment, certification,
    # and project-history signals are no longer used to compute the radar —
    # mastery is driven exclusively by demonstrated quiz performance.
    # Self-assessment ratings stored in profile_skill_assessments are preserved
    # in the DB as part of the locked profile record but are not passed here.
    events_result = await db.execute(
        select(SkillProfileEvent)
        .where(
            SkillProfileEvent.practitioner_id == practitioner_id,
            SkillProfileEvent.source == "quiz_attempt",
        )
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

    # ── 3. Curriculum Planner ──────────────────────────────────────────────
    # Build skill score context from ALL skills in the catalog.
    # Skills the profiler scored get their real scores; everything else
    # defaults to mastery=0 / confidence=0 so the planner always has real
    # skill IDs to choose from and never has to invent them.
    all_skills_result = await db.execute(select(Skill))
    all_skills: list[Skill] = list(all_skills_result.scalars().all())
    valid_skill_ids: set[str] = {s.id for s in all_skills}

    profiler_score_map = {s.skill_id: s for s in profiler_output.skill_scores}

    skill_scores_context: list[SkillScoreContext] = []
    for skill in all_skills:
        if skill.id in profiler_score_map:
            scored = profiler_score_map[skill.id]
            skill_scores_context.append(
                SkillScoreContext(
                    skill_id=skill.id,
                    skill_name=skill.name,
                    mastery_score=scored.mastery_score,
                    confidence=scored.confidence,
                )
            )
        else:
            # No profiler data yet — treat as completely unscored
            skill_scores_context.append(
                SkillScoreContext(
                    skill_id=skill.id,
                    skill_name=skill.name,
                    mastery_score=0.0,
                    confidence=0.0,
                )
            )

    # Upsert snapshots for ALL skills in the catalog (not just profiler-scored
    # ones). This ensures the Skill Radar always has data to display, even for
    # brand-new practitioners who have no skill_profile_events yet.
    now = datetime.now(UTC)
    for skill_ctx in skill_scores_context:
        existing = await db.get(
            SkillProfileSnapshot, (practitioner_id, skill_ctx.skill_id)
        )
        if existing is not None:
            existing.mastery_score = skill_ctx.mastery_score
            existing.confidence = skill_ctx.confidence
            existing.last_computed_at = now
        else:
            db.add(SkillProfileSnapshot(
                practitioner_id=practitioner_id,
                skill_id=skill_ctx.skill_id,
                mastery_score=skill_ctx.mastery_score,
                confidence=skill_ctx.confidence,
                last_computed_at=now,
            ))
    await db.flush()

    # Append mastery history rows for skills the Skill Profiler actually scored
    # (mastery_score > 0 means the profiler had real signal, not just a zero-pad).
    # These rows feed the ProgressTrendChart and the AdoptionTrendChart baseline.
    for skill_ctx in skill_scores_context:
        if skill_ctx.mastery_score > 0.0:
            db.add(MasteryHistory(
                id=str(uuid.uuid4()),
                practitioner_id=practitioner_id,
                skill_id=skill_ctx.skill_id,
                mastery_score=skill_ctx.mastery_score,
                recorded_at=now,
            ))
    await db.flush()

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

    # Safety guard: drop any path items whose skill_id isn't in the DB.
    # This prevents FK violations if the model ignores the "don't invent IDs" rule.
    valid_path_items = [
        item for item in planner_output.path_items
        if item.skill_id in valid_skill_ids
    ]
    if len(valid_path_items) < len(planner_output.path_items):
        invalid_ids = [
            item.skill_id for item in planner_output.path_items
            if item.skill_id not in valid_skill_ids
        ]
        import logging
        logging.getLogger(__name__).warning(
            "Curriculum Planner returned %d invalid skill IDs (dropped): %s",
            len(invalid_ids), invalid_ids,
        )
        planner_output.path_items = valid_path_items

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
    # Mark any previously active paths as completed so there is exactly one
    # active path at a time.
    prev_paths_result = await db.execute(
        select(LearningPath).where(
            LearningPath.practitioner_id == practitioner_id,
            LearningPath.status == "active",
        )
    )
    for prev in prev_paths_result.scalars().all():
        prev.status = "completed"

    learning_path_id = str(uuid.uuid4())
    learning_path = LearningPath(
        id=learning_path_id,
        practitioner_id=practitioner_id,
        generated_at=datetime.now(UTC),
        status="active",
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
