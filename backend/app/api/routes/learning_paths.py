"""Learning paths, items, and attempts API.

Routes:
  POST /learning-paths/generate                              trigger generate_learning_path workflow
  GET  /practitioners/{id}/learning-paths                    list paths for a practitioner
  POST /practitioners/{id}/learning-paths/{path_id}/quiz-batch  generate one quiz item per skill (Phase 12.2)
  GET  /items?skill_id=                                      list items for a skill (Phase 4 QuizRunner)
  POST /attempts                                             submit an attempt (triggers Grader)
  GET  /attempts/{attempt_id}                                fetch a scored attempt
  GET  /practitioners/{id}/certification-domain-scores       domain readiness scores

Step 5.2 — Auth applied:
  - POST /learning-paths/generate → require_any_authenticated + body self-enforcement
  - GET  /practitioners/{id}/learning-paths → require_any_authenticated + self-enforcement
  - POST quiz-batch → require_any_authenticated + self-enforcement
  - GET  /items → require_any_authenticated
  - POST /attempts → require_any_authenticated + body self-enforcement
  - GET  /attempts/{id} → require_any_authenticated + ownership check (self or admin)
"""

import uuid
from datetime import UTC, datetime
from typing import Literal

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
from app.db.models import (
    Attempt,
    Certification,
    CertificationDomain,
    CertificationDomainScore,
    Item,
    LearningPath,
    LearningPathItem,
    Practitioner,
    PractitionerProfile,
    Skill,
    SkillProfileEvent,
    SkillProfileSnapshot,
)
from app.db.session import get_db
from app.schemas.cert_domain_versions import CertificationDomainScoreRead
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
    """Trigger the generate_learning_path workflow (Skill Profiler → Curriculum Planner).

    Quiz questions are generated separately on first Quiz tab open via POST quiz-batch.
    """
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


# ── Quiz batch generation (Phase 12.2) ────────────────────────────────────────


@router.post(
    "/practitioners/{practitioner_id}/learning-paths/{path_id}/quiz-batch",
    status_code=201,
)
async def generate_quiz_batch(
    practitioner_id: str,
    path_id: str,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> dict:
    """Generate one starter MCQ per skill in the path via a single LLM call.

    Called by the frontend Quiz tab on first open when no items exist for the path.
    Returns the IDs of the newly created Item rows; the frontend refetches items
    via the existing GET /items?skill_id= hooks to populate each skill tab.
    """
    enforce_self_or_admin(session, practitioner_id)

    # Validate path belongs to practitioner
    path = await db.get(LearningPath, path_id)
    if path is None or path.practitioner_id != practitioner_id:
        raise HTTPException(status_code=404, detail="Learning path not found")

    # Fetch path skill IDs (ordered by sequence)
    path_items_result = await db.execute(
        select(LearningPathItem)
        .where(LearningPathItem.learning_path_id == path_id)
        .order_by(LearningPathItem.sequence_order)
    )
    path_items = path_items_result.scalars().all()
    if not path_items:
        raise HTTPException(status_code=422, detail="Learning path has no skills")

    skill_ids = [pi.skill_id for pi in path_items]

    # Fetch skills metadata
    skills_result = await db.execute(
        select(Skill).where(Skill.id.in_(skill_ids))
    )
    skills_by_id: dict[str, Skill] = {s.id: s for s in skills_result.scalars().all()}

    # Fetch mastery snapshots
    snapshots_result = await db.execute(
        select(SkillProfileSnapshot).where(
            SkillProfileSnapshot.practitioner_id == practitioner_id,
            SkillProfileSnapshot.skill_id.in_(skill_ids),
        )
    )
    mastery_by_skill: dict[str, float] = {
        snap.skill_id: float(snap.mastery_score)
        for snap in snapshots_result.scalars().all()
    }

    # Fetch active profile for cert context
    profile_result = await db.execute(
        select(PractitionerProfile).where(
            PractitionerProfile.practitioner_id == practitioner_id,
            PractitionerProfile.is_active == True,  # noqa: E712
        )
    )
    active_profile = profile_result.scalar_one_or_none()

    cert_code = "UNKNOWN"
    cert_name = "Unknown Certification"
    certification_domains_for_batch: list[dict] | None = None

    if active_profile and active_profile.certification_id:
        cert = await db.get(Certification, active_profile.certification_id)
        if cert:
            cert_code = cert.code
            cert_name = cert.name
        domains_result = await db.execute(
            select(CertificationDomain).where(
                CertificationDomain.certification_id == active_profile.certification_id
            ).order_by(CertificationDomain.sequence_order)
        )
        cert_domains = domains_result.scalars().all()
        cert_domains_map = {d.id: d for d in cert_domains}
        if cert_domains:
            certification_domains_for_batch = [
                {
                    "id": d.id,
                    "name": d.domain_name,
                    "description": d.domain_description,
                    "weight_pct": float(d.weight_pct),
                }
                for d in cert_domains
            ]

    # Count prior generations per skill (to vary question style on re-generations)
    from sqlalchemy import func as sa_func
    prior_counts_result = await db.execute(
        select(Item.skill_id, sa_func.count(Item.id))
        .where(Item.skill_id.in_(skill_ids))
        .group_by(Item.skill_id)
    )
    prior_counts: dict[str, int] = {row[0]: row[1] for row in prior_counts_result.all()}

    # Build SkillQuizSpec list
    from app.agents.quiz_batch_generator import QuizBatchGeneratorAgent, QuizBatchGeneratorInput, SkillQuizSpec

    skill_specs: list[SkillQuizSpec] = []
    for skill_id in skill_ids:
        skill = skills_by_id.get(skill_id)
        if skill is None:
            continue

        # Determine cert domain for this skill (best-effort match by category / name)
        # For now: no FK from skills → cert_domains; leave domain as None.
        # The agent receives full domain context via certification_domains.
        skill_specs.append(SkillQuizSpec(
            skill_id=skill_id,
            skill_name=skill.name,
            skill_description=skill.description,
            mastery_score=mastery_by_skill.get(skill_id, 0.0),
            certification_domain_id=None,
            certification_domain_name=None,
            is_cert_evaluated=False,
            prior_generation_count=prior_counts.get(skill_id, 0),
        ))

    if not skill_specs:
        raise HTTPException(status_code=422, detail="No valid skills found in path")

    batch_input = QuizBatchGeneratorInput(
        skills=skill_specs,
        cert_code=cert_code,
        cert_name=cert_name,
        certification_domains=certification_domains_for_batch,
    )

    model_client = create_model_client()
    agent = QuizBatchGeneratorAgent(client=model_client, db_session=db)
    batch_output = await agent.run(batch_input)

    # Persist generated items
    item_ids: list[str] = []
    for quiz_item in batch_output.items:
        item_id = str(uuid.uuid4())
        item = Item(
            id=item_id,
            skill_id=quiz_item.skill_id,
            item_type=quiz_item.item_type,
            prompt=quiz_item.prompt,
            answer_key=quiz_item.answer_key.model_dump(),
            trap_explanation=quiz_item.trap_explanation,
            difficulty=quiz_item.difficulty,
            calibration_stats={"attempt_count": 0, "total_score": 0.0, "trap_selection_count": 0},
            certification_domain_id=quiz_item.certification_domain_id,
            is_cert_evaluated=quiz_item.is_cert_evaluated,
            generation=1,
        )
        db.add(item)
        item_ids.append(item_id)

    await db.commit()
    return {"item_ids": item_ids}


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
    items = result.scalars().all()

    # Enrich with domain name if available
    out: list[ItemRead] = []
    for item in items:
        domain_name: str | None = None
        if item.certification_domain_id:
            domain = await db.get(CertificationDomain, item.certification_domain_id)
            if domain:
                domain_name = domain.domain_name

        read = ItemRead(
            id=item.id,
            skill_id=item.skill_id,
            item_type=item.item_type,
            prompt=item.prompt,
            answer_key=item.answer_key,
            trap_explanation=item.trap_explanation,
            difficulty=float(item.difficulty),
            calibration_stats=item.calibration_stats,
            created_at=item.created_at,
            certification_domain_id=item.certification_domain_id,
            is_cert_evaluated=item.is_cert_evaluated,
            certification_domain_name=domain_name,
            generation=item.generation,
        )
        out.append(read)

    return out


# ── Domain-gap scores ─────────────────────────────────────────────────────────

@router.get(
    "/practitioners/{practitioner_id}/certification-domain-scores",
    response_model=list[CertificationDomainScoreRead],
)
async def get_certification_domain_scores(
    practitioner_id: str,
    certification_id: str = Query(..., description="Filter by certification ID"),
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> list[CertificationDomainScoreRead]:
    """Return per-domain mastery scores for a practitioner, ordered by sequence_order."""
    enforce_self_or_admin(session, practitioner_id)

    practitioner = await db.get(Practitioner, practitioner_id)
    if practitioner is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")

    # Get all domains for this cert, ordered by sequence
    domains_result = await db.execute(
        select(CertificationDomain)
        .where(CertificationDomain.certification_id == certification_id)
        .order_by(CertificationDomain.sequence_order)
    )
    domains = domains_result.scalars().all()

    out: list[CertificationDomainScoreRead] = []
    for domain in domains:
        score_result = await db.execute(
            select(CertificationDomainScore).where(
                CertificationDomainScore.practitioner_id == practitioner_id,
                CertificationDomainScore.certification_domain_id == domain.id,
            )
        )
        score = score_result.scalar_one_or_none()

        if score is None:
            continue  # no score yet for this domain

        mastery_score = float(score.mastery_score)
        previous = float(score.previous_mastery_score) if score.previous_mastery_score is not None else None
        mastery_delta: float | None = None
        trend: str = "new"

        if previous is not None:
            mastery_delta = mastery_score - previous
            if abs(mastery_delta) <= 0.01:
                trend = "stable"
            elif mastery_delta > 0:
                trend = "improving"
            else:
                trend = "declining"

        out.append(CertificationDomainScoreRead(
            id=score.id,
            certification_domain_id=domain.id,
            domain_name=domain.domain_name,
            weight_pct=float(domain.weight_pct),
            sequence_order=domain.sequence_order,
            mastery_score=mastery_score,
            confidence=float(score.confidence),
            source=score.source,
            last_computed_at=score.last_computed_at,
            previous_mastery_score=previous,
            mastery_delta=mastery_delta,
            trend=trend,
        ))

    return out


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
