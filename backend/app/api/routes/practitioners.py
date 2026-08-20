"""Practitioners API — CRUD + skill profile read.

Step 2.1 scenarios:
  - Creating then fetching a practitioner returns matching data.
  - Fetching a nonexistent practitioner returns 404, not a 500.

Step 5.2 — Auth applied:
  - GET  /practitioners               → require_admin (list all practitioners)
  - POST /practitioners               → require_admin (admin creates; login creates practitioners)
  - GET  /practitioners/{id}          → require_any_authenticated + self-enforcement
  - PATCH /practitioners/{id}         → require_any_authenticated + self-enforcement
  - GET  /practitioners/{id}/skill-profile → require_any_authenticated + self-enforcement

Phase 21 additions:
  - PATCH /admin/practitioners/{id}/deactivate   → require_admin only
  - PATCH /admin/practitioners/{id}/reactivate   → require_admin only
  - GET   /admin/practitioners/{id}/activity-summary → require_admin_or_leadership
"""

import uuid
from datetime import UTC, datetime, date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.session import (
    SessionInfo,
    enforce_self_or_admin,
    require_admin,
    require_admin_or_leadership,
    require_any_authenticated,
)
from app.db.models import (
    Attempt,
    ByteSizedLesson,
    Certification,
    CertificationDomain,
    CertificationSkill,
    Item,
    LearningPath,
    LearningPathItem,
    LessonRead,
    MockExamSession,
    Practitioner,
    PractitionerProfile,
    Skill,
    SkillProfileEvent,
    SkillProfileSnapshot,
)
from app.db.session import get_db
from app.schemas.practitioners import (
    ActivityMockExamRow,
    ActivitySkillRow,
    ActivitySummaryResponse,
    ActivitySummaryStats,
    PractitionerCreate,
    PractitionerRead,
    PractitionerUpdate,
    SelfAssessmentRequest,
    SelfAssessmentResponse,
    SkillSnapshotRead,
)

router = APIRouter(prefix="/practitioners", tags=["practitioners"])


@router.post("", response_model=PractitionerRead, status_code=201)
async def create_practitioner(
    body: PractitionerCreate,
    db: AsyncSession = Depends(get_db),
    _session: SessionInfo = Depends(require_admin),
) -> PractitionerRead:
    """Create a new practitioner. Admin only — normal practitioners are created via login."""
    practitioner = Practitioner(
        id=str(uuid.uuid4()),
        name=body.name,
        email=body.email,
        role=body.role,
        practice=body.practice,
        seniority_level=body.seniority_level,
    )
    db.add(practitioner)
    await db.commit()
    await db.refresh(practitioner)
    return PractitionerRead.model_validate(practitioner)


@router.get("", response_model=list[PractitionerRead])
async def list_practitioners(
    db: AsyncSession = Depends(get_db),
    _session: SessionInfo = Depends(require_admin),
) -> list[PractitionerRead]:
    """List all practitioners. Admin only."""
    result = await db.execute(select(Practitioner).order_by(Practitioner.name))
    practitioners = result.scalars().all()
    return [PractitionerRead.model_validate(p) for p in practitioners]


@router.get("/{practitioner_id}", response_model=PractitionerRead)
async def get_practitioner(
    practitioner_id: str,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> PractitionerRead:
    """Fetch one practitioner. Practitioner sees own data; full admin sees all."""
    enforce_self_or_admin(session, practitioner_id)
    practitioner = await db.get(Practitioner, practitioner_id)
    if practitioner is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")
    return PractitionerRead.model_validate(practitioner)


@router.patch("/{practitioner_id}", response_model=PractitionerRead)
async def update_practitioner(
    practitioner_id: str,
    body: PractitionerUpdate,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> PractitionerRead:
    """Partial update of practitioner fields. Practitioner edits own; admin edits any."""
    enforce_self_or_admin(session, practitioner_id)
    practitioner = await db.get(Practitioner, practitioner_id)
    if practitioner is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(practitioner, field, value)
    await db.commit()
    await db.refresh(practitioner)
    return PractitionerRead.model_validate(practitioner)


@router.post(
    "/{practitioner_id}/self-assessment",
    response_model=SelfAssessmentResponse,
    status_code=201,
)
async def submit_self_assessment(
    practitioner_id: str,
    body: SelfAssessmentRequest,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> SelfAssessmentResponse:
    """Record a practitioner's self-assessed skill levels.

    Each assessment item writes one skill_profile_event with source='self_assessment'.
    These events are read by the Skill Profiler the next time a learning path is
    generated, updating the mastery scores and the Skill Radar.

    Skips any skill_id not present in the skills catalog (avoids FK violations if
    the client sends a stale ID).
    """
    enforce_self_or_admin(session, practitioner_id)
    practitioner = await db.get(Practitioner, practitioner_id)
    if practitioner is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")

    # Build a set of valid skill IDs to guard against stale client data
    valid_skills_result = await db.execute(select(Skill.id))
    valid_skill_ids: set[str] = {row[0] for row in valid_skills_result.all()}

    now = datetime.now(UTC)
    written = 0
    for item in body.assessments:
        if item.skill_id not in valid_skill_ids:
            continue  # silently skip unknown skills
        db.add(SkillProfileEvent(
            id=str(uuid.uuid4()),
            practitioner_id=practitioner_id,
            skill_id=item.skill_id,
            source="self_assessment",
            signal_strength=item.signal_strength,
            occurred_at=now,
            metadata_=None,
        ))
        written += 1

    await db.commit()
    return SelfAssessmentResponse(events_written=written)


@router.get("/{practitioner_id}/skill-profile", response_model=list[SkillSnapshotRead])
async def get_skill_profile(
    practitioner_id: str,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> list[SkillSnapshotRead]:
    """Return a practitioner's current skill profile with optional domain enrichment.

    Phase 13.4: when the practitioner's active profile has a certification with
    agent-discovered skills, each snapshot is enriched with its domain name and
    weight for color-coded radar display.
    """
    enforce_self_or_admin(session, practitioner_id)
    practitioner = await db.get(Practitioner, practitioner_id)
    if practitioner is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")

    # Fetch snapshots + skill names
    result = await db.execute(
        select(SkillProfileSnapshot, Skill)
        .join(Skill, Skill.id == SkillProfileSnapshot.skill_id)
        .where(SkillProfileSnapshot.practitioner_id == practitioner_id)
        .order_by(SkillProfileSnapshot.mastery_score.desc())
    )
    rows = result.all()

    # Phase 13.4: build domain lookup from agent_discovered cert skills.
    # skill_id → (domain_id, domain_name, domain_weight_pct)
    domain_by_skill: dict[str, tuple[str, str, float]] = {}

    active_profile_result = await db.execute(
        select(PractitionerProfile).where(
            PractitionerProfile.practitioner_id == practitioner_id,
            PractitionerProfile.is_active == True,  # noqa: E712
        )
    )
    active_profile = active_profile_result.scalar_one_or_none()

    if active_profile is not None and active_profile.certification_id is not None:
        # Prefer agent_discovered; fall back to seed if none
        ad_result = await db.execute(
            select(CertificationSkill).where(
                CertificationSkill.certification_id == active_profile.certification_id,
                CertificationSkill.source == "agent_discovered",
                CertificationSkill.certification_domain_id != None,  # noqa: E711
            )
        )
        cert_skills = ad_result.scalars().all()

        if not cert_skills:
            # Fallback to seed rows that have a domain link
            seed_result = await db.execute(
                select(CertificationSkill).where(
                    CertificationSkill.certification_id == active_profile.certification_id,
                    CertificationSkill.certification_domain_id != None,  # noqa: E711
                )
            )
            cert_skills = seed_result.scalars().all()

        for cs in cert_skills:
            if cs.certification_domain_id:
                domain = await db.get(CertificationDomain, cs.certification_domain_id)
                if domain:
                    domain_by_skill[cs.skill_id] = (
                        domain.id,
                        domain.domain_name,
                        float(domain.weight_pct),
                    )

    # Build response
    out: list[SkillSnapshotRead] = []
    for snap, skill in rows:
        domain_info = domain_by_skill.get(snap.skill_id)
        out.append(SkillSnapshotRead(
            skill_id=snap.skill_id,
            skill_name=skill.name,
            mastery_score=float(snap.mastery_score),
            confidence=float(snap.confidence),
            last_computed_at=snap.last_computed_at,
            certification_domain_id=domain_info[0] if domain_info else None,
            certification_domain_name=domain_info[1] if domain_info else None,
            domain_weight_pct=domain_info[2] if domain_info else None,
        ))

    return out


# ── Phase 21: deactivate / reactivate (admin-only) ───────────────────────────

@router.patch("/{practitioner_id}/deactivate", status_code=204)
async def deactivate_practitioner(
    practitioner_id: str,
    db: AsyncSession = Depends(get_db),
    _session: SessionInfo = Depends(require_admin),
) -> None:
    """Block a practitioner from logging in. Data is fully preserved. Admin only."""
    practitioner = await db.get(Practitioner, practitioner_id)
    if practitioner is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")
    if not practitioner.is_active:
        return  # already deactivated — idempotent
    practitioner.is_active = False
    await db.commit()


@router.patch("/{practitioner_id}/reactivate", status_code=204)
async def reactivate_practitioner(
    practitioner_id: str,
    db: AsyncSession = Depends(get_db),
    _session: SessionInfo = Depends(require_admin),
) -> None:
    """Re-enable a previously deactivated practitioner. Admin only."""
    practitioner = await db.get(Practitioner, practitioner_id)
    if practitioner is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")
    if practitioner.is_active:
        return  # already active — idempotent
    practitioner.is_active = True
    await db.commit()


# ── Phase 21: activity summary (admin + leadership) ──────────────────────────

@router.get(
    "/{practitioner_id}/activity-summary",
    response_model=ActivitySummaryResponse,
)
async def get_activity_summary(
    practitioner_id: str,
    db: AsyncSession = Depends(get_db),
    _session: SessionInfo = Depends(require_admin_or_leadership),
) -> ActivitySummaryResponse:
    """Return full engagement history for the admin Activity tab.

    Aggregates:
      - Quiz attempts per skill (rounds = distinct calendar days, correct/wrong counts)
      - Skill mastery snapshots with gap %
      - Lesson reads per byte-sized lesson, joined to skills
      - Mock exam sessions with certification code
    """
    practitioner = await db.get(Practitioner, practitioner_id)
    if practitioner is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")

    # ── 1. All skill snapshots (mastery + gap) ────────────────────────────────
    snap_result = await db.execute(
        select(SkillProfileSnapshot, Skill)
        .join(Skill, Skill.id == SkillProfileSnapshot.skill_id)
        .where(SkillProfileSnapshot.practitioner_id == practitioner_id)
        .order_by(SkillProfileSnapshot.mastery_score.desc())
    )
    snapshot_rows = snap_result.all()
    # skill_id → (mastery_score, skill_name, gap_pct)
    skill_meta: dict[str, tuple[float, str, int]] = {}
    for snap, skill in snapshot_rows:
        mastery = float(snap.mastery_score)
        skill_meta[snap.skill_id] = (mastery, skill.name, round((1.0 - mastery) * 100))

    # ── 2. Quiz attempt aggregates per skill ──────────────────────────────────
    # Per-skill: distinct-day count (rounds), correct (score=1.0), wrong (score=0.0)
    attempt_result = await db.execute(
        select(
            Item.skill_id,
            func.count(func.distinct(func.date(Attempt.attempted_at))).label("quiz_rounds"),
            func.sum(case((Attempt.score >= 0.99, 1), else_=0)).label("correct_count"),
            func.sum(case((Attempt.score < 0.01, 1), else_=0)).label("wrong_count"),
            func.count(Attempt.id).label("total_count"),
        )
        .join(Item, Item.id == Attempt.item_id)
        .where(Attempt.practitioner_id == practitioner_id)
        .group_by(Item.skill_id)
    )
    attempt_by_skill: dict[str, dict] = {}
    for row in attempt_result.all():
        attempt_by_skill[row.skill_id] = {
            "quiz_rounds": int(row.quiz_rounds or 0),
            "correct_count": int(row.correct_count or 0),
            "wrong_count": int(row.wrong_count or 0),
            "total_count": int(row.total_count or 0),
        }

    # Global attempt totals (for summary cards)
    global_total = sum(v["total_count"] for v in attempt_by_skill.values())
    global_correct = sum(v["correct_count"] for v in attempt_by_skill.values())
    global_rounds = sum(v["quiz_rounds"] for v in attempt_by_skill.values())
    overall_correct_pct = round(global_correct / global_total * 100) if global_total else 0

    # ── 3. Lesson-read aggregates per skill ────────────────────────────────────
    lesson_result = await db.execute(
        select(
            ByteSizedLesson.skill_id,
            func.sum(LessonRead.duration_seconds).label("total_seconds"),
            func.count(LessonRead.id).label("lesson_count"),
            func.max(LessonRead.started_at).label("last_read_at"),
        )
        .join(ByteSizedLesson, ByteSizedLesson.id == LessonRead.lesson_id)
        .where(LessonRead.practitioner_id == practitioner_id)
        .group_by(ByteSizedLesson.skill_id)
    )
    lesson_by_skill: dict[str, dict] = {}
    for row in lesson_result.all():
        lesson_by_skill[row.skill_id] = {
            "total_seconds": int(row.total_seconds or 0),
            "lesson_count": int(row.lesson_count or 0),
            "last_read_at": row.last_read_at,
        }

    total_lesson_seconds = sum(v["total_seconds"] for v in lesson_by_skill.values())

    # ── 4. Build per-skill activity rows ──────────────────────────────────────
    # Union: skills from snapshots + skills from attempts (some may lack snapshots)
    all_skill_ids: set[str] = set(skill_meta.keys()) | set(attempt_by_skill.keys())

    # For skills without snapshots, fetch name from Skill table
    missing_skill_ids = all_skill_ids - set(skill_meta.keys())
    if missing_skill_ids:
        extra_skills_result = await db.execute(
            select(Skill).where(Skill.id.in_(missing_skill_ids))
        )
        for extra_skill in extra_skills_result.scalars().all():
            skill_meta[extra_skill.id] = (0.0, extra_skill.name, 100)

    skill_activity: list[ActivitySkillRow] = []
    for sid in sorted(all_skill_ids):
        mastery, skill_name, gap_pct = skill_meta.get(sid, (0.0, sid, 100))
        att = attempt_by_skill.get(sid, {"quiz_rounds": 0, "correct_count": 0, "wrong_count": 0, "total_count": 0})
        les = lesson_by_skill.get(sid, {"total_seconds": 0, "lesson_count": 0, "last_read_at": None})
        total = att["total_count"]
        correct_pct = round(att["correct_count"] / total * 100) if total else 0
        skill_activity.append(ActivitySkillRow(
            skill_id=sid,
            skill_name=skill_name,
            mastery_score=mastery,
            gap_pct=gap_pct,
            quiz_rounds=att["quiz_rounds"],
            correct_count=att["correct_count"],
            wrong_count=att["wrong_count"],
            correct_pct=correct_pct,
            total_lesson_seconds=les["total_seconds"],
            lesson_count=les["lesson_count"],
            last_lesson_read_at=les["last_read_at"],
        ))

    # Sort: highest gap first (most urgent)
    skill_activity.sort(key=lambda r: r.gap_pct, reverse=True)

    # ── 5. Mock exam sessions ──────────────────────────────────────────────────
    mock_result = await db.execute(
        select(MockExamSession, Certification)
        .join(Certification, Certification.id == MockExamSession.certification_id)
        .where(MockExamSession.practitioner_id == practitioner_id)
        .order_by(MockExamSession.started_at.desc())
    )
    mock_rows = mock_result.all()

    mock_exams: list[ActivityMockExamRow] = []
    mock_completed_count = 0
    latest_mock_score_pct: int | None = None

    for mock, cert in mock_rows:
        score_pct: int | None = None
        if mock.score is not None:
            score_pct = round(float(mock.score) * 100)
        if mock.status == "completed":
            mock_completed_count += 1
            if latest_mock_score_pct is None and score_pct is not None:
                latest_mock_score_pct = score_pct  # most recent completed score

        answered = mock.correct_count if mock.correct_count is not None else 0
        mock_exams.append(ActivityMockExamRow(
            session_id=mock.id,
            certification_code=cert.code,
            status=mock.status,
            score_pct=score_pct,
            questions_answered=answered,
            total_questions=mock.total_count,
            time_spent_seconds=mock.time_elapsed_seconds,
            started_at=mock.started_at,
            completed_at=mock.completed_at,
            abandoned_reason=mock.abandoned_reason,
        ))

    # ── 6. Assemble response ──────────────────────────────────────────────────
    return ActivitySummaryResponse(
        summary_stats=ActivitySummaryStats(
            total_quiz_rounds=global_rounds,
            total_attempts=global_total,
            overall_correct_pct=overall_correct_pct,
            total_lesson_seconds=total_lesson_seconds,
            mock_exams_completed=mock_completed_count,
            latest_mock_score_pct=latest_mock_score_pct,
        ),
        skill_activity=skill_activity,
        mock_exams=mock_exams,
    )
