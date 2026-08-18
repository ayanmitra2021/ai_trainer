"""Learning paths, items, and attempts API.

Routes:
  POST /learning-paths/generate                              trigger generate_learning_path workflow
  GET  /practitioners/{id}/learning-paths                    list paths for a practitioner
  POST /practitioners/{id}/learning-paths/{path_id}/quiz-batch  admin/manual quiz batch override (Phase 17)
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

import random
import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func as sa_func
from sqlalchemy import select, update as sa_update
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
from app.agents.quiz_batch_generator import (
    QuizBatchGeneratorAgent,
    QuizBatchGeneratorInput,
    SkillQuizSpec,
)
from app.db.session import AsyncSessionLocal, get_db
from app.schemas.cert_domain_versions import CertificationDomainScoreRead
from app.schemas.items import AttemptCreate, AttemptRead, GraderInput, GraderOutput, ItemRead, MCQAnswerKey
from app.schemas.learning_paths import (
    GenerateLearningPathRequest,
    GenerateLearningPathResponse,
    LearningPathRead,
)
from app.workflows.generate_learning_path import run_generate_learning_path

router = APIRouter(tags=["learning_paths"])


# ── Phase 17: Quiz batch helpers ──────────────────────────────────────────────


async def _check_quiz_exhaustion(
    practitioner_id: str,
    skill_ids: list[str],
    db: AsyncSession,
) -> tuple[bool, bool]:
    """Return (should_generate, is_first_time).

    (True, True)  — no items exist → first generation
    (True, False) — all items have attempts → exhausted → refresh
    (False, False)— unanswered items remain → skip
    """
    if not skill_ids:
        return False, False
    items_result = await db.execute(
        select(Item.id).where(Item.skill_id.in_(skill_ids))
    )
    item_ids = [row[0] for row in items_result.all()]
    if not item_ids:
        return True, True
    attempted_result = await db.execute(
        select(Attempt.item_id).distinct().where(
            Attempt.practitioner_id == practitioner_id,
            Attempt.item_id.in_(item_ids),
        )
    )
    attempted_ids = {row[0] for row in attempted_result.all()}
    all_answered = set(item_ids) <= attempted_ids
    return all_answered, False


async def _compute_skill_avg_scores(
    practitioner_id: str,
    skill_ids: list[str],
    db: AsyncSession,
) -> dict[str, float]:
    """Per-skill average attempt score — used to adjust difficulty on refresh."""
    result = await db.execute(
        select(Item.skill_id, sa_func.avg(Attempt.score))
        .join(Attempt, Attempt.item_id == Item.id)
        .where(
            Item.skill_id.in_(skill_ids),
            Attempt.practitioner_id == practitioner_id,
        )
        .group_by(Item.skill_id)
    )
    return {row[0]: float(row[1]) for row in result.all()}


def _assign_question_counts(skill_specs: list, target_min: int = 10, target_max: int = 12) -> None:
    """Mutate skill_specs in-place: set question_count (1 or 2) so total ∈ [target_min, target_max].

    Cert-evaluated skills are prioritised for 2-question slots.
    """
    n = len(skill_specs)
    if n == 0:
        return
    lo = max(target_min, n)
    hi = min(target_max, n * 2)
    if lo > hi:
        # More skills than target_max — each gets exactly 1 question
        for spec in skill_specs:
            spec.question_count = 1
        return
    target = random.randint(lo, hi)
    extra = target - n
    for spec in skill_specs:
        spec.question_count = 1
    if extra <= 0:
        return
    cert_idx = [i for i, s in enumerate(skill_specs) if s.is_cert_evaluated]
    supp_idx = [i for i, s in enumerate(skill_specs) if not s.is_cert_evaluated]
    double: set[int] = set()
    c = min(extra, len(cert_idx))
    if c > 0:
        double.update(random.sample(cert_idx, c))
    extra -= c
    if extra > 0 and supp_idx:
        s2 = min(extra, len(supp_idx))
        if s2 > 0:
            double.update(random.sample(supp_idx, s2))
    for i, spec in enumerate(skill_specs):
        if i in double:
            spec.question_count = 2


async def _build_quiz_spec_list(
    practitioner_id: str,
    skill_ids: list[str],
    db: AsyncSession,
    *,
    avg_score_by_skill: dict[str, float] | None = None,
) -> "tuple[list, str, str, list[dict] | None]":
    """Fetch cert context and build SkillQuizSpec list ready for quiz generation.

    Returns (skill_specs, cert_code, cert_name, certification_domains).
    Does NOT call _assign_question_counts — caller is responsible.
    avg_score_by_skill: when provided, mastery is adjusted per skill for difficulty.
    """
    import logging as _log

    if not skill_ids:
        return [], "UNKNOWN", "Unknown Certification", None

    # ── Skill metadata ────────────────────────────────────────────────────────
    skills_result = await db.execute(select(Skill).where(Skill.id.in_(skill_ids)))
    skills_by_id: dict[str, Skill] = {s.id: s for s in skills_result.scalars().all()}

    snapshots_result = await db.execute(
        select(SkillProfileSnapshot).where(
            SkillProfileSnapshot.practitioner_id == practitioner_id,
            SkillProfileSnapshot.skill_id.in_(skill_ids),
        )
    )
    mastery_by_skill = {
        snap.skill_id: float(snap.mastery_score)
        for snap in snapshots_result.scalars().all()
    }

    # ── Cert context ──────────────────────────────────────────────────────────
    profile_result = await db.execute(
        select(PractitionerProfile).where(
            PractitionerProfile.practitioner_id == practitioner_id,
            PractitionerProfile.is_active == True,  # noqa: E712
        )
    )
    active_profile = profile_result.scalar_one_or_none()

    cert_code, cert_name = "UNKNOWN", "Unknown Certification"
    certification_domains_for_batch: list[dict] | None = None
    cert_skill_ids: set[str] = set()

    if active_profile and active_profile.certification_id:
        from app.db.models import CertificationSkill
        cert = await db.get(Certification, active_profile.certification_id)
        if cert:
            cert_code = cert.code
            cert_name = cert.name
        cert_skills_result = await db.execute(
            select(CertificationSkill).where(
                CertificationSkill.certification_id == active_profile.certification_id
            )
        )
        cert_skill_ids = {cs.skill_id for cs in cert_skills_result.scalars().all()}
        domains_result = await db.execute(
            select(CertificationDomain)
            .where(CertificationDomain.certification_id == active_profile.certification_id)
            .order_by(CertificationDomain.sequence_order)
        )
        cert_domains = domains_result.scalars().all()
        if cert_domains:
            certification_domains_for_batch = [
                {"id": d.id, "name": d.domain_name, "description": d.domain_description,
                 "weight_pct": float(d.weight_pct)}
                for d in cert_domains
            ]

    # ── Prior generation counts and prompts ───────────────────────────────────
    prior_counts_result = await db.execute(
        select(Item.skill_id, sa_func.count(Item.id))
        .where(Item.skill_id.in_(skill_ids))
        .group_by(Item.skill_id)
    )
    prior_counts = {row[0]: row[1] for row in prior_counts_result.all()}

    prompts_result = await db.execute(
        select(Item.skill_id, Item.prompt).where(Item.skill_id.in_(skill_ids))
    )
    prior_prompts_by_skill: dict[str, list[str]] = {}
    for row in prompts_result.all():
        prior_prompts_by_skill.setdefault(row[0], []).append(row[1])

    # ── Build specs ───────────────────────────────────────────────────────────
    skill_specs: list[SkillQuizSpec] = []
    for skill_id in skill_ids:
        skill = skills_by_id.get(skill_id)
        if skill is None:
            continue
        mastery = mastery_by_skill.get(skill_id, 0.0)
        if avg_score_by_skill is not None:
            avg = avg_score_by_skill.get(skill_id)
            if avg is not None:
                if avg >= 1.0:
                    mastery = min(mastery + 0.25, 0.95)
                elif avg < 0.5:
                    mastery = max(mastery - 0.10, 0.05)

        skill_specs.append(SkillQuizSpec(
            skill_id=skill_id,
            skill_name=skill.name,
            skill_description=skill.description,
            mastery_score=mastery,
            is_cert_evaluated=skill_id in cert_skill_ids,
            prior_generation_count=prior_counts.get(skill_id, 0),
            prior_prompts=prior_prompts_by_skill.get(skill_id, []),
        ))

    return skill_specs, cert_code, cert_name, certification_domains_for_batch


async def _generate_quizzes_progressively(
    practitioner_id: str,
    learning_path_id: str,
    skill_specs: list,
    cert_code: str,
    cert_name: str,
    certification_domains: list[dict] | None,
) -> None:
    """Background task: one LLM call per skill, 1-2 questions each.

    Opens its own AsyncSession — the request session is closed before this runs.
    NVIDIA is primary; Haiku is only used if all NVIDIA tiers fail for that skill.
    Per-skill failures set quiz_status='failed' and continue to the next skill.
    """
    import logging as _bg_logging

    _bg_log = _bg_logging.getLogger(__name__)

    async with AsyncSessionLocal() as db:
        for spec in skill_specs:
            try:
                batch_input = QuizBatchGeneratorInput(
                    skills=[spec],
                    cert_code=cert_code,
                    cert_name=cert_name,
                    certification_domains=certification_domains,
                )
                model_client = create_model_client()
                agent = QuizBatchGeneratorAgent(client=model_client, db_session=db)
                batch_output = await agent.run(batch_input)

                # Compute generation number fresh — avoids stale data on retries
                max_gen_q = await db.execute(
                    select(sa_func.max(Item.generation)).where(Item.skill_id == spec.skill_id)
                )
                gen = (max_gen_q.scalar() or 0) + 1

                for quiz_item in batch_output.items:
                    db.add(Item(
                        id=str(uuid.uuid4()),
                        skill_id=quiz_item.skill_id,
                        item_type=quiz_item.item_type,
                        prompt=quiz_item.prompt,
                        answer_key=quiz_item.answer_key.model_dump(),
                        trap_explanation=quiz_item.trap_explanation,
                        difficulty=quiz_item.difficulty,
                        calibration_stats={"attempt_count": 0, "total_score": 0.0, "trap_selection_count": 0},
                        certification_domain_id=quiz_item.certification_domain_id,
                        is_cert_evaluated=quiz_item.is_cert_evaluated,
                        generation=gen,
                    ))

                await db.execute(
                    sa_update(LearningPathItem)
                    .where(
                        LearningPathItem.learning_path_id == learning_path_id,
                        LearningPathItem.skill_id == spec.skill_id,
                    )
                    .values(quiz_status="ready")
                )
                await db.commit()
                _bg_log.info(
                    "quiz_progress: skill=%s items=%d gen=%d",
                    spec.skill_id, len(batch_output.items), gen,
                )

            except Exception as exc:  # noqa: BLE001
                _bg_log.warning(
                    "quiz_progress: skill=%s FAILED: %s — marking failed",
                    spec.skill_id, exc,
                )
                try:
                    await db.rollback()
                    await db.execute(
                        sa_update(LearningPathItem)
                        .where(
                            LearningPathItem.learning_path_id == learning_path_id,
                            LearningPathItem.skill_id == spec.skill_id,
                        )
                        .values(quiz_status="failed")
                    )
                    await db.commit()
                except Exception as status_err:  # noqa: BLE001
                    _bg_log.error(
                        "quiz_progress: could not mark skill=%s as failed: %s",
                        spec.skill_id, status_err,
                    )


# ── Learning path generation ───────────────────────────────────────────────────

@router.post("/learning-paths/generate", response_model=GenerateLearningPathResponse, status_code=202)
async def generate_learning_path(
    body: GenerateLearningPathRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> GenerateLearningPathResponse:
    """Trigger the generate_learning_path workflow (Skill Profiler → Curriculum Planner).

    Phase 17.7: Quiz questions are generated progressively in a background task,
    one skill at a time, so the HTTP response returns immediately.
    - First time (no items) → launch background generation for all skills.
    - Regeneration with all items answered → launch background with difficulty adjustment.
    - Regeneration with unanswered items → skip quiz generation entirely.
    """
    enforce_self_or_admin(session, body.practitioner_id)
    practitioner = await db.get(Practitioner, body.practitioner_id)
    if practitioner is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")

    model_client = create_model_client()
    response = await run_generate_learning_path(
        practitioner_id=body.practitioner_id,
        db=db,
        claude_client=model_client,
    )

    # ── Phase 17.7: progressive background quiz generation ────────────────────
    new_path_items_result = await db.execute(
        select(LearningPathItem)
        .where(LearningPathItem.learning_path_id == response.learning_path_id)
        .order_by(LearningPathItem.sequence_order)
    )
    new_skill_ids = [pi.skill_id for pi in new_path_items_result.scalars().all()]

    practitioner_id = body.practitioner_id
    should_gen, is_first = await _check_quiz_exhaustion(
        practitioner_id, new_skill_ids, db
    )
    if should_gen:
        avg_scores = (
            None if is_first
            else await _compute_skill_avg_scores(practitioner_id, new_skill_ids, db)
        )
        skill_specs, cert_code, cert_name, cert_domains = await _build_quiz_spec_list(
            practitioner_id, new_skill_ids, db, avg_score_by_skill=avg_scores
        )
        if skill_specs:
            _assign_question_counts(skill_specs)
            background_tasks.add_task(
                _generate_quizzes_progressively,
                practitioner_id,
                response.learning_path_id,
                skill_specs,
                cert_code,
                cert_name,
                cert_domains,
            )
            response.quiz_generating = True
    else:
        response.quiz_skipped_reason = "unanswered_items"

    return response


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


# ── Quiz batch generation (Phase 17: admin/manual override) ──────────────────


@router.post(
    "/practitioners/{practitioner_id}/learning-paths/{path_id}/quiz-batch",
    status_code=202,
)
async def generate_quiz_batch(
    practitioner_id: str,
    path_id: str,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> dict:
    """Admin/manual endpoint to force quiz generation for a path (all skills).

    Phase 17.8: Now calls the same progressive per-skill background engine
    synchronously (awaits completion) — suitable for admin tooling where
    the caller can wait. For non-blocking generation use POST /learning-paths/generate.
    """
    enforce_self_or_admin(session, practitioner_id)

    path = await db.get(LearningPath, path_id)
    if path is None or path.practitioner_id != practitioner_id:
        raise HTTPException(status_code=404, detail="Learning path not found")

    path_items_result = await db.execute(
        select(LearningPathItem)
        .where(LearningPathItem.learning_path_id == path_id)
        .order_by(LearningPathItem.sequence_order)
    )
    path_items = path_items_result.scalars().all()
    if not path_items:
        raise HTTPException(status_code=422, detail="Learning path has no skills")

    skill_ids = [pi.skill_id for pi in path_items]

    # Reset any previously-failed skills to pending before regenerating
    await db.execute(
        sa_update(LearningPathItem)
        .where(
            LearningPathItem.learning_path_id == path_id,
            LearningPathItem.quiz_status.in_(["failed", "ready"]),
        )
        .values(quiz_status="pending")
    )
    await db.commit()

    skill_specs, cert_code, cert_name, cert_domains = await _build_quiz_spec_list(
        practitioner_id, skill_ids, db
    )
    if skill_specs:
        _assign_question_counts(skill_specs)
        await _generate_quizzes_progressively(
            practitioner_id, path_id, skill_specs, cert_code, cert_name, cert_domains
        )

    return {"quiz_generating": False, "skills_queued": len(skill_specs)}


@router.post(
    "/practitioners/{practitioner_id}/quiz-generation/retry",
    status_code=202,
)
async def retry_quiz_generation(
    practitioner_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> dict:
    """Re-attempt quiz generation for all skills in a status='failed' state.

    Phase 17.9: Fetches the most recent active learning path, resets
    failed items to 'pending', and relaunches background generation for
    only those skills. Idempotent — safe to call multiple times.
    """
    enforce_self_or_admin(session, practitioner_id)

    # Fetch the most recent learning path for the practitioner
    path_result = await db.execute(
        select(LearningPath)
        .where(LearningPath.practitioner_id == practitioner_id)
        .order_by(LearningPath.generated_at.desc())
        .limit(1)
    )
    latest_path = path_result.scalar_one_or_none()
    if latest_path is None:
        raise HTTPException(status_code=404, detail="No learning path found")

    # Find items that need generation: failed OR stuck-pending (background task
    # never ran or crashed before updating quiz_status to ready/failed).
    stuck_result = await db.execute(
        select(LearningPathItem)
        .where(
            LearningPathItem.learning_path_id == latest_path.id,
            LearningPathItem.quiz_status.in_(["failed", "pending"]),
        )
        .order_by(LearningPathItem.sequence_order)
    )
    stuck_items = stuck_result.scalars().all()
    if not stuck_items:
        return {"message": "No skills need generation", "retried": 0}

    stuck_skill_ids = [si.skill_id for si in stuck_items]

    # Ensure all stuck items are in pending state before relaunching
    await db.execute(
        sa_update(LearningPathItem)
        .where(
            LearningPathItem.learning_path_id == latest_path.id,
            LearningPathItem.skill_id.in_(stuck_skill_ids),
        )
        .values(quiz_status="pending")
    )
    await db.commit()

    failed_skill_ids = stuck_skill_ids  # reuse variable name for the rest of the function

    skill_specs, cert_code, cert_name, cert_domains = await _build_quiz_spec_list(
        practitioner_id, failed_skill_ids, db
    )
    if skill_specs:
        _assign_question_counts(skill_specs)
        background_tasks.add_task(
            _generate_quizzes_progressively,
            practitioner_id,
            latest_path.id,
            skill_specs,
            cert_code,
            cert_name,
            cert_domains,
        )

    return {"message": "Retry launched", "retried": len(skill_specs)}


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

def _grade_mcq_instantly(
    item_answer_key: dict,
    submitted_response: dict,
) -> GraderOutput | None:
    """Phase 16: deterministic MCQ grading — no LLM call required.

    Returns a GraderOutput when the item's answer_key contains pre-generated
    rationales (correct_rationale + incorrect_rationale), or None when those
    fields are absent (legacy items generated before Phase 16) so the caller
    can fall back to GraderAgent.

    Score rules (same as the grader prompt):
      - 1.0  if selected_index == correct_index
      - 0.0  otherwise
    is_trap_selected is True when the wrong option chosen is the trap_index.
    """
    ak = MCQAnswerKey.model_validate(item_answer_key)
    if ak.correct_rationale is None or ak.incorrect_rationale is None:
        return None  # legacy item — use GraderAgent

    selected: int | None = submitted_response.get("selected_index")
    if selected is None:
        return None  # malformed response — fall back to GraderAgent

    is_correct = selected == ak.correct_index
    score = 1.0 if is_correct else 0.0
    is_trap_selected = (
        (selected == ak.trap_index)
        if (not is_correct and ak.trap_index is not None)
        else None
    )
    rationale = ak.correct_rationale if is_correct else ak.incorrect_rationale
    return GraderOutput(
        score=score,
        grader_rationale=rationale,
        is_trap_selected=is_trap_selected,
    )


@router.post("/attempts", response_model=AttemptRead, status_code=201)
async def submit_attempt(
    body: AttemptCreate,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> AttemptRead:
    """Submit a practitioner's response to an item and get it graded immediately.

    Phase 16: MCQ items generated since Phase 16 carry pre-generated rationales
    in answer_key (correct_rationale + incorrect_rationale).  Those items are
    graded deterministically in Python — no LLM call, feedback is instant.
    Legacy MCQ items and all free-text items still go through GraderAgent.
    """
    enforce_self_or_admin(session, body.practitioner_id)
    practitioner = await db.get(Practitioner, body.practitioner_id)
    if practitioner is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")

    item = await db.get(Item, body.item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    # ── Phase 16: instant MCQ grading (no LLM) ───────────────────────────────
    grader_output: GraderOutput | None = None
    if item.item_type == "mcq":
        grader_output = _grade_mcq_instantly(item.answer_key, body.response)

    # ── Fallback: GraderAgent for free-text or legacy MCQ items ──────────────
    if grader_output is None:
        from app.agents.grader import GraderAgent
        from app.agents.model_client import AllProvidersUnavailableError, ProviderUnavailableError

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
        grader_output = await agent.run(grader_input)

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
