"""Learning paths and attempts API.

Routes:
  POST /learning-paths/generate          trigger generate_learning_path workflow
  GET  /practitioners/{id}/learning-paths  list paths for a practitioner
  POST /attempts                          submit an attempt (triggers Grader)
  GET  /attempts/{attempt_id}             fetch a scored attempt
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db.models import Attempt, Item, LearningPath, Practitioner
from app.db.session import get_db
from app.schemas.items import AttemptCreate, AttemptRead, GraderInput, GraderOutput
from app.schemas.learning_paths import (
    GenerateLearningPathRequest,
    GenerateLearningPathResponse,
    LearningPathRead,
)

router = APIRouter(tags=["learning_paths"])


# ── Learning path generation ───────────────────────────────────────────────────

@router.post("/learning-paths/generate", response_model=GenerateLearningPathResponse, status_code=202)
async def generate_learning_path(
    body: GenerateLearningPathRequest,
    db: AsyncSession = Depends(get_db),
) -> GenerateLearningPathResponse:
    """Trigger the generate_learning_path workflow (Skill Profiler → Curriculum Planner → Item-Writer)."""
    practitioner = await db.get(Practitioner, body.practitioner_id)
    if practitioner is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")

    from app.workflows.generate_learning_path import run_generate_learning_path
    import anthropic as anthropic_lib

    anthropic_client = anthropic_lib.AsyncAnthropic(api_key=settings.anthropic_api_key)
    result = await run_generate_learning_path(
        practitioner_id=body.practitioner_id,
        db=db,
        claude_client=anthropic_client,
    )
    return result


@router.get(
    "/practitioners/{practitioner_id}/learning-paths",
    response_model=list[LearningPathRead],
)
async def list_learning_paths(
    practitioner_id: str, db: AsyncSession = Depends(get_db)
) -> list[LearningPathRead]:
    """Return all learning paths for a practitioner, newest first."""
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


# ── Attempts ───────────────────────────────────────────────────────────────────

@router.post("/attempts", response_model=AttemptRead, status_code=201)
async def submit_attempt(
    body: AttemptCreate,
    db: AsyncSession = Depends(get_db),
) -> AttemptRead:
    """Submit a practitioner's response to an item and get it graded immediately."""
    practitioner = await db.get(Practitioner, body.practitioner_id)
    if practitioner is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")

    item = await db.get(Item, body.item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    # Run the Grader agent
    from app.agents.grader import GraderAgent
    import anthropic as anthropic_lib

    anthropic_client = anthropic_lib.AsyncAnthropic(api_key=settings.anthropic_api_key)
    grader_input = GraderInput(
        item_id=body.item_id,
        item_type=item.item_type,
        item_prompt=item.prompt,
        answer_key=item.answer_key,
        trap_explanation=item.trap_explanation,
        submitted_response=body.response,
    )
    agent = GraderAgent(client=anthropic_client, db_session=db)
    grader_output: GraderOutput = await agent.run(grader_input)

    # Persist the attempt
    attempt = Attempt(
        id=str(uuid.uuid4()),
        practitioner_id=body.practitioner_id,
        item_id=body.item_id,
        response=body.response,
        score=grader_output.score,
        grader_rationale=grader_output.grader_rationale,
        is_trap_selected=grader_output.is_trap_selected,
        attempted_at=datetime.now(UTC),
    )
    db.add(attempt)

    # Update calibration stats on the item
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


@router.get("/attempts/{attempt_id}", response_model=AttemptRead)
async def get_attempt(
    attempt_id: str, db: AsyncSession = Depends(get_db)
) -> AttemptRead:
    """Fetch a scored attempt by ID."""
    attempt = await db.get(Attempt, attempt_id)
    if attempt is None:
        raise HTTPException(status_code=404, detail="Attempt not found")
    return AttemptRead.model_validate(attempt)
