"""Learning paths, items, and attempts API.

Routes:
  POST /learning-paths/generate          trigger generate_learning_path workflow
  GET  /practitioners/{id}/learning-paths  list paths for a practitioner
  GET  /items?skill_id=                  list items for a skill (Phase 4 QuizRunner)
  POST /attempts                          submit an attempt (triggers Grader)
  GET  /attempts/{attempt_id}             fetch a scored attempt

Step 5.2 — Auth applied:
  - POST /learning-paths/generate → require_any_authenticated + body self-enforcement
  - GET  /practitioners/{id}/learning-paths → require_any_authenticated + self-enforcement
  - GET  /items → require_any_authenticated
  - POST /attempts → require_any_authenticated + body self-enforcement
  - GET  /attempts/{id} → require_any_authenticated + ownership check (self or admin)
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.base import ModelClient
from app.agents.model_client import create_model_client
from app.api.deps.session import (
    SessionInfo,
    enforce_self_or_admin,
    require_any_authenticated,
)
from app.config import settings
from app.db.models import Attempt, Item, LearningPath, Practitioner, SkillProfileEvent
from app.db.session import get_db
from app.schemas.items import AttemptCreate, AttemptRead, GraderInput, GraderOutput, ItemRead
from app.schemas.learning_paths import (
    GenerateLearningPathRequest,
    GenerateLearningPathResponse,
    LearningPathRead,
)
from app.workflows.generate_learning_path import run_generate_learning_path

router = APIRouter(tags=["learning_paths"])


# ── Learning path generation ───────────────────────────────────────────────────

@router.post("/learning-paths/generate", response_model=GenerateLearningPathResponse, status_code=202)
async def generate_learning_path(
    body: GenerateLearningPathRequest,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> GenerateLearningPathResponse:
    """Trigger the generate_learning_path workflow (Skill Profiler → Curriculum Planner → Item-Writer)."""
    enforce_self_or_admin(session, body.practitioner_id)
    practitioner = await db.get(Practitioner, body.practitioner_id)
    if practitioner is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")

    model_client = create_model_client()
    result = await run_generate_learning_path(
        practitioner_id=body.practitioner_id,
        db=db,
        claude_client=model_client,
    )
    return result


@router.get(
    "/practitioners/{practitioner_id}/learning-paths",
    response_model=list[LearningPathRead],
)
async def list_learning_paths(
    practitioner_id: str,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> list[LearningPathRead]:
    """Return all learning paths for a practitioner, newest first."""
    enforce_self_or_admin(session, practitioner_id)
    practitioner = await db.get(Practitioner, practitioner_id)
    if practitioner is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")

    result = await db.execute(
        select(LearningPath)
        .options(selectinload(LearningPath.items))
        .where(LearningPath.practitioner_id == practitioner_id)
        .order_by(LearningPath.generated_at.desc())
    )
    paths = result.scalars().all()
    return [LearningPathRead.model_validate(p) for p in paths]


# ── Items ─────────────────────────────────────────────────────────────────────

@router.get("/items", response_model=list[ItemRead])
async def list_items_by_skill(
    skill_id: str = Query(..., description="Filter items by skill ID"),
    db: AsyncSession = Depends(get_db),
    _session: SessionInfo = Depends(require_any_authenticated),
) -> list[ItemRead]:
    """Return all items for a given skill, newest first. Used by the QuizRunner."""
    result = await db.execute(
        select(Item)
        .where(Item.skill_id == skill_id)
        .order_by(Item.created_at.desc())
    )
    return [ItemRead.model_validate(i) for i in result.scalars().all()]


# ── Attempts ───────────────────────────────────────────────────────────────────

@router.post("/attempts", response_model=AttemptRead, status_code=201)
async def submit_attempt(
    body: AttemptCreate,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> AttemptRead:
    """Submit a practitioner's response to an item and get it graded immediately."""
    enforce_self_or_admin(session, body.practitioner_id)
    practitioner = await db.get(Practitioner, body.practitioner_id)
    if practitioner is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")

    item = await db.get(Item, body.item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    from app.agents.grader import GraderAgent

    model_client = create_model_client()
    grader_input = GraderInput(
        item_id=body.item_id,
        item_type=item.item_type,
        item_prompt=item.prompt,
        answer_key=item.answer_key,
        trap_explanation=item.trap_explanation,
        submitted_response=body.response,
    )
    agent = GraderAgent(client=model_client, db_session=db)
    grader_output: GraderOutput = await agent.run(grader_input)

    now = datetime.now(UTC)
    attempt = Attempt(
        id=str(uuid.uuid4()),
        practitioner_id=body.practitioner_id,
        item_id=body.item_id,
        response=body.response,
        score=grader_output.score,
        grader_rationale=grader_output.grader_rationale,
        is_trap_selected=grader_output.is_trap_selected,
        attempted_at=now,
    )
    db.add(attempt)

    # Write a skill_profile_event so the quiz result feeds into the next
    # Skill Profiler run (and therefore the Skill Radar).
    db.add(SkillProfileEvent(
        id=str(uuid.uuid4()),
        practitioner_id=body.practitioner_id,
        skill_id=item.skill_id,
        source="quiz_attempt",
        signal_strength=float(grader_output.score),
        occurred_at=now,
        metadata_={"attempt_id": attempt.id, "item_id": body.item_id},
    ))

    stats = item.calibration_stats or {
        "attempt_count": 0,
        "total_score": 0.0,
        "trap_selection_count": 0,
    }
    stats["attempt_count"] += 1
    stats["total_score"] += float(grader_output.score)
    if grader_output.is_trap_selected:
        stats["trap_selection_count"] += 1
    stats["avg_score"] = stats["total_score"] / stats["attempt_count"]
    item.calibration_stats = stats

    await db.commit()
    await db.refresh(attempt)
    return AttemptRead.model_validate(attempt)


@router.get(
    "/practitioners/{practitioner_id}/attempts",
    response_model=list[AttemptRead],
)
async def list_attempts(
    practitioner_id: str,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> list[AttemptRead]:
    """Return all attempts for a practitioner, newest first.

    Used by the QuizRunner to restore answered-question state across navigation.
    """
    enforce_self_or_admin(session, practitioner_id)
    practitioner = await db.get(Practitioner, practitioner_id)
    if practitioner is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")

    result = await db.execute(
        select(Attempt)
        .where(Attempt.practitioner_id == practitioner_id)
        .order_by(Attempt.attempted_at.desc())
    )
    return [AttemptRead.model_validate(a) for a in result.scalars().all()]


@router.get("/attempts/{attempt_id}", response_model=AttemptRead)
async def get_attempt(
    attempt_id: str,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> AttemptRead:
    """Fetch a scored attempt by ID.

    Practitioner may only fetch their own attempts. Full admins fetch any.
    Leadership admins are denied (individual data is off-limits to leadership).
    """
    attempt = await db.get(Attempt, attempt_id)
    if attempt is None:
        raise HTTPException(status_code=404, detail="Attempt not found")

    # Ownership check: same logic as enforce_self_or_admin but using attempt.practitioner_id
    enforce_self_or_admin(session, attempt.practitioner_id)
    return AttemptRead.model_validate(attempt)
