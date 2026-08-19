"""Byte-Sized Lessons API — Phase 18.3.

Routes:
  POST /practitioners/{id}/byte-sized-lessons/generate     trigger generation (background)
  GET  /practitioners/{id}/byte-sized-lessons              list all lessons (current + history)
  GET  /practitioners/{id}/byte-sized-lessons/{lesson_id}  full lesson detail
  POST /practitioners/{id}/byte-sized-lessons/{lesson_id}/read-sessions         open a read session
  PATCH /practitioners/{id}/byte-sized-lessons/{lesson_id}/read-sessions/{sid}  close a read session

Generation priority (per Phase 18.4 redesign):
  1. Skills with incorrectly answered quiz attempts (score == 0) — lesson targets
     the specific misconception demonstrated by the wrong answer.
  2. Skills in the path with low mastery but no quiz evidence yet — broad coverage.
  3. Skills with incorrectly answered mock exam questions — lesson targets the
     specific misconception from the mock exam wrong answer.
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func as sa_func, select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.byte_sized_lesson import (
    ByteSizedLessonAgent,
    ByteSizedLessonInput,
    WrongAnswerEvidence,
)
from app.agents.model_client import create_model_client
from app.api.deps.session import (
    SessionInfo,
    enforce_self_or_admin,
    require_any_authenticated,
)
from app.db.models import (
    Attempt,
    ByteSizedLesson,
    CertificationDomain,
    CertificationSkill,
    Item,
    LearningPath,
    LearningPathItem,
    LessonRead,
    MockExamQuestion,
    MockExamSession,
    Practitioner,
    PractitionerProfile,
    Skill,
    SkillProfileSnapshot,
)
from app.db.session import AsyncSessionLocal, get_db

router = APIRouter(tags=["byte_sized_lessons"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────


class LessonSummary(BaseModel):
    id: str
    skill_id: str
    skill_name: str
    gap_pct: float
    target_pct: float
    what_missing: str | None
    estimated_read_minutes: int | None
    generation_status: str
    path_generation_seq: int
    total_read_seconds: int | None
    last_read_at: str | None

    model_config = {"from_attributes": True}


class LessonDetail(LessonSummary):
    content_md: str | None
    external_links: list[dict] | None


class LessonListResponse(BaseModel):
    current: list[LessonSummary]
    history: list[LessonSummary]


class ReadSessionCreate(BaseModel):
    pass


class ReadSessionClose(BaseModel):
    duration_seconds: int


class ReadSessionResponse(BaseModel):
    session_id: str
    started_at: str


# ── Wrong-answer evidence collection ─────────────────────────────────────────


async def _collect_wrong_quiz_evidence(
    practitioner_id: str,
    skill_ids: list[str],
    db: AsyncSession,
) -> dict[str, list[WrongAnswerEvidence]]:
    """Return wrong-answer evidence from quiz attempts, keyed by skill_id.

    Takes the 3 most recent wrong attempts per skill, deduplicating by question
    text so repeated errors on the same question appear once.
    Only attempts with score == 0.0 are included.
    """
    if not skill_ids:
        return {}

    result = await db.execute(
        select(Attempt, Item)
        .join(Item, Attempt.item_id == Item.id)
        .where(
            Attempt.practitioner_id == practitioner_id,
            Attempt.score == 0.0,
            Item.skill_id.in_(skill_ids),
        )
        .order_by(Attempt.attempted_at.desc())
    )
    rows = result.all()

    by_skill: dict[str, list[WrongAnswerEvidence]] = {}
    seen_per_skill: dict[str, set[str]] = {}  # skill_id → set of question_text keys already added

    for attempt, item in rows:
        skill_id = item.skill_id
        question_key = item.prompt[:100]  # dedup key — first 100 chars of prompt
        if skill_id not in seen_per_skill:
            seen_per_skill[skill_id] = set()
        if question_key in seen_per_skill[skill_id]:
            continue
        if len(by_skill.get(skill_id, [])) >= 2:
            continue  # cap at 2 per skill

        opts: list[str] = item.answer_key.get("options", [])
        user_idx: int | None = (attempt.response or {}).get("selected_index")
        correct_idx: int = item.answer_key.get("correct_index", 0)

        user_text = opts[user_idx] if (user_idx is not None and 0 <= user_idx < len(opts)) else "Unknown"
        correct_text = opts[correct_idx] if 0 <= correct_idx < len(opts) else "Unknown"

        # Best available explanation of the misconception, in priority order:
        #   1. grader_rationale (from GraderAgent or pre-generated incorrect_rationale)
        #   2. incorrect_rationale stored in answer_key (Phase 16+)
        #   3. trap_explanation (when the wrong answer was the trap option)
        misconception = (
            attempt.grader_rationale
            or item.answer_key.get("incorrect_rationale")
            or item.trap_explanation
            or ""
        )

        evidence = WrongAnswerEvidence(
            question_text=item.prompt,
            user_selected_text=user_text,
            correct_answer_text=correct_text,
            misconception_explanation=misconception,
            source="quiz",
        )
        by_skill.setdefault(skill_id, []).append(evidence)
        seen_per_skill[skill_id].add(question_key)

    return by_skill


async def _collect_wrong_mock_evidence(
    practitioner_id: str,
    skill_ids: list[str],
    skills_by_id: dict[str, Skill],
    db: AsyncSession,
) -> dict[str, list[WrongAnswerEvidence]]:
    """Return wrong-answer evidence from completed mock exam sessions, keyed by skill_id.

    MockExamQuestion uses skill_name (not skill_id) — we resolve via the skills map.
    Only questions from *completed* sessions are considered.
    """
    if not skill_ids or not skills_by_id:
        return {}

    # Build skill_name → skill_id map for the path's skills only
    name_to_skill_id: dict[str, str] = {
        s.name: s.id
        for sid, s in skills_by_id.items()
        if s is not None and sid in skill_ids
    }
    if not name_to_skill_id:
        return {}

    result = await db.execute(
        select(MockExamQuestion, MockExamSession.completed_at)
        .join(MockExamSession, MockExamQuestion.session_id == MockExamSession.id)
        .where(
            MockExamSession.practitioner_id == practitioner_id,
            MockExamSession.status == "completed",
            MockExamQuestion.score == 0.0,
            MockExamQuestion.skill_name.in_(list(name_to_skill_id.keys())),
        )
        .order_by(MockExamSession.completed_at.desc())
    )
    rows = result.all()

    by_skill: dict[str, list[WrongAnswerEvidence]] = {}
    seen_per_skill: dict[str, set[str]] = {}

    for q, _completed_at in rows:
        skill_id = name_to_skill_id.get(q.skill_name)
        if skill_id is None:
            continue
        question_key = q.prompt[:100]
        if skill_id not in seen_per_skill:
            seen_per_skill[skill_id] = set()
        if question_key in seen_per_skill[skill_id]:
            continue
        if len(by_skill.get(skill_id, [])) >= 2:
            continue

        opts: list[str] = q.answer_key.get("options", [])
        user_idx: int | None = (q.response or {}).get("selected_index")
        correct_idx: int = q.answer_key.get("correct_index", 0)

        user_text = opts[user_idx] if (user_idx is not None and 0 <= user_idx < len(opts)) else "Unknown"
        correct_text = opts[correct_idx] if 0 <= correct_idx < len(opts) else "Unknown"

        misconception = (
            q.trap_explanation
            or q.answer_key.get("explanation")
            or ""
        )

        evidence = WrongAnswerEvidence(
            question_text=q.prompt,
            user_selected_text=user_text,
            correct_answer_text=correct_text,
            misconception_explanation=misconception,
            source="mock_exam",
        )
        by_skill.setdefault(skill_id, []).append(evidence)
        seen_per_skill[skill_id].add(question_key)

    return by_skill


def _skill_sort_key(
    item: LearningPathItem,
    mastery_by_skill: dict[str, float],
    wrong_quiz: dict[str, list],
    wrong_mock: dict[str, list],
) -> tuple[int, float]:
    """Sort key for lesson generation order.

    Returns (priority_bucket, -mastery_score) so within each bucket the
    most-behind skills are generated first.

    Bucket 0 — Priority 1: has wrong quiz answers         → highest urgency
    Bucket 1 — Priority 2: no quiz evidence, low mastery  → skill gap
    Bucket 2 — Priority 3: has wrong mock exam answers    → exam experience gap
    Bucket 3 — No evidence, on track                      → lowest urgency
    """
    skill_id = item.skill_id
    mastery = mastery_by_skill.get(skill_id, 0.0)

    if skill_id in wrong_quiz:
        return (0, -mastery)
    if mastery < 0.55 and skill_id not in wrong_mock:
        return (1, -mastery)
    if skill_id in wrong_mock:
        return (2, -mastery)
    return (3, -mastery)


# ── Background generation engine ──────────────────────────────────────────────


async def _generate_byte_sized_lessons(
    practitioner_id: str,
    learning_path_id: str,
    path_generation_seq: int,
) -> None:
    """Background task: one LLM call per skill gap, ordered by evidence priority.

    Priority 1 — Wrong quiz answers: lesson targets the specific misconception.
    Priority 2 — Low mastery, no quiz data yet: broad skill-gap coverage.
    Priority 3 — Wrong mock exam answers: lesson targets mock exam misconception.

    Opens its own AsyncSession — the request session is closed before this runs.
    Per-skill failures are isolated (log WARNING, continue).
    If the top-level session or setup fails, all pending lessons for this seq
    are marked 'failed' so they never stay stuck in 'pending' forever.
    """
    import logging as _log
    _logger = _log.getLogger(__name__)

    model_client = create_model_client()

    async with AsyncSessionLocal() as db:
        try:
            # ── Fetch path items ──────────────────────────────────────────────
            path_items_result = await db.execute(
                select(LearningPathItem)
                .where(LearningPathItem.learning_path_id == learning_path_id)
                .order_by(LearningPathItem.sequence_order)
            )
            path_items = list(path_items_result.scalars().all())
            skill_ids = [pi.skill_id for pi in path_items]

            # ── Fetch cert context ────────────────────────────────────────────
            profile_result = await db.execute(
                select(PractitionerProfile).where(
                    PractitionerProfile.practitioner_id == practitioner_id,
                    PractitionerProfile.is_active == True,  # noqa: E712
                )
            )
            profile = profile_result.scalars().first()
            cert_name = "your certification"
            domain_version_id = None
            if profile:
                from app.db.models import Certification
                cert = await db.get(Certification, profile.certification_id)
                if cert:
                    cert_name = cert.name
                domain_version_id = profile.domain_version_id

            # ── Fetch mastery snapshots ───────────────────────────────────────
            snapshots_result = await db.execute(
                select(SkillProfileSnapshot).where(
                    SkillProfileSnapshot.practitioner_id == practitioner_id,
                    SkillProfileSnapshot.skill_id.in_(skill_ids),
                )
            )
            mastery_by_skill = {
                s.skill_id: float(s.mastery_score)
                for s in snapshots_result.scalars().all()
            }

            # ── Fetch skill objects (needed for mock-exam name→id resolution) ─
            skills_result = await db.execute(
                select(Skill).where(Skill.id.in_(skill_ids))
            )
            skills_by_id: dict[str, Skill] = {s.id: s for s in skills_result.scalars().all()}

            # ── Fetch domains, keyed by domain id ─────────────────────────────
            domains_by_id: dict[str, CertificationDomain] = {}
            if domain_version_id:
                domains_result = await db.execute(
                    select(CertificationDomain).where(
                        CertificationDomain.domain_version_id == domain_version_id
                    )
                )
                domains_by_id = {d.id: d for d in domains_result.scalars().all()}

            # ── Build skill → domain map via certification_skills ─────────────
            skill_domain_map: dict[str, CertificationDomain] = {}
            if profile and domains_by_id:
                cs_result = await db.execute(
                    select(CertificationSkill).where(
                        CertificationSkill.certification_id == profile.certification_id,
                        CertificationSkill.skill_id.in_(skill_ids),
                        CertificationSkill.certification_domain_id.isnot(None),
                    )
                )
                for cs in cs_result.scalars().all():
                    if cs.certification_domain_id in domains_by_id:
                        skill_domain_map[cs.skill_id] = domains_by_id[cs.certification_domain_id]

            # ── Collect wrong-answer evidence (Priority 1 and 3) ─────────────
            wrong_quiz = await _collect_wrong_quiz_evidence(
                practitioner_id, skill_ids, db
            )
            wrong_mock = await _collect_wrong_mock_evidence(
                practitioner_id, skill_ids, skills_by_id, db
            )

            _logger.info(
                "byte_sized_lesson: evidence — %d skills with wrong quiz answers, "
                "%d with wrong mock answers",
                len(wrong_quiz), len(wrong_mock),
            )

            # ── Sort path items by priority ───────────────────────────────────
            sorted_items = sorted(
                path_items,
                key=lambda pi: _skill_sort_key(pi, mastery_by_skill, wrong_quiz, wrong_mock),
            )

            # ── Generate one lesson per skill ─────────────────────────────────
            for item in sorted_items:
                # Fetch lesson row (already created as pending)
                lesson_result = await db.execute(
                    select(ByteSizedLesson).where(
                        ByteSizedLesson.practitioner_id == practitioner_id,
                        ByteSizedLesson.learning_path_id == learning_path_id,
                        ByteSizedLesson.skill_id == item.skill_id,
                        ByteSizedLesson.path_generation_seq == path_generation_seq,
                    )
                )
                lesson = lesson_result.scalars().first()
                if lesson is None:
                    _logger.warning(
                        "byte_sized_lesson: no lesson row for skill=%s — skipping", item.skill_id
                    )
                    continue

                # Skip already-generated lessons (retry resets only failed/pending rows)
                if lesson.generation_status == "ready":
                    _logger.debug(
                        "byte_sized_lesson: skill=%s already ready — skipping", item.skill_id
                    )
                    continue

                try:
                    skill = skills_by_id.get(item.skill_id)
                    mastery = mastery_by_skill.get(item.skill_id, 0.0)

                    # Domain context
                    domain_name = "General AI Knowledge"
                    domain_description = "Core AI and machine learning concepts"
                    if item.skill_id in skill_domain_map:
                        d = skill_domain_map[item.skill_id]
                        domain_name = d.domain_name
                        domain_description = d.domain_description or domain_name

                    # Assemble wrong-answer evidence in priority order:
                    #   Priority 1 — quiz wrong answers
                    #   Priority 3 — mock exam wrong answers (only if no quiz evidence)
                    wrong_evidence: list[WrongAnswerEvidence] = (
                        wrong_quiz.get(item.skill_id)
                        or wrong_mock.get(item.skill_id)
                        or []
                    )

                    priority_label = (
                        "quiz_wrong_answer" if item.skill_id in wrong_quiz
                        else "mock_exam_wrong_answer" if item.skill_id in wrong_mock
                        else "skill_gap"
                    )

                    agent_input = ByteSizedLessonInput(
                        skill_name=skill.name if skill else lesson.skill_name,
                        skill_description=skill.description or "" if skill else "",
                        current_mastery_score=mastery,
                        target_mastery_score=0.85,
                        certification_name=cert_name,
                        domain_name=domain_name,
                        domain_description=domain_description,
                        wrong_answers=wrong_evidence,
                    )

                    agent = ByteSizedLessonAgent(client=model_client, db_session=db)
                    output = await agent.run(agent_input)

                    lesson.what_missing = output.what_missing
                    lesson.content_md = output.content_md
                    lesson.external_links = [lnk.model_dump() for lnk in output.external_links]
                    lesson.estimated_read_minutes = output.estimated_read_minutes
                    lesson.generation_status = "ready"
                    await db.commit()

                    _logger.info(
                        "byte_sized_lesson: skill=%s status=ready priority=%s wrong_answers=%d",
                        item.skill_id, priority_label, len(wrong_evidence),
                    )

                except Exception as exc:  # noqa: BLE001
                    _logger.warning(
                        "byte_sized_lesson: skill=%s FAILED: %s", item.skill_id, exc
                    )
                    try:
                        await db.rollback()
                        lesson.generation_status = "failed"
                        await db.commit()
                    except Exception as err2:  # noqa: BLE001
                        _logger.error(
                            "byte_sized_lesson: could not mark skill=%s failed: %s",
                            item.skill_id, err2,
                        )

        except Exception as top_exc:  # noqa: BLE001
            # Top-level failure — mark ALL remaining pending lessons as failed
            # so they never get stuck in 'pending' forever.
            _logger.error(
                "byte_sized_lesson: top-level task failure for seq=%d: %s — marking all pending as failed",
                path_generation_seq, top_exc,
            )
            try:
                await db.rollback()
                await db.execute(
                    sa_update(ByteSizedLesson)
                    .where(
                        ByteSizedLesson.practitioner_id == practitioner_id,
                        ByteSizedLesson.learning_path_id == learning_path_id,
                        ByteSizedLesson.path_generation_seq == path_generation_seq,
                        ByteSizedLesson.generation_status == "pending",
                    )
                    .values(generation_status="failed")
                )
                await db.commit()
            except Exception as cleanup_err:  # noqa: BLE001
                _logger.error("byte_sized_lesson: cleanup also failed: %s", cleanup_err)


def _build_lesson_summary(lesson: ByteSizedLesson, reads: list[LessonRead]) -> LessonSummary:
    total_secs = sum(r.duration_seconds for r in reads if r.duration_seconds is not None) or None
    if total_secs == 0:
        total_secs = None
    last_read = max((r.started_at for r in reads), default=None)
    return LessonSummary(
        id=lesson.id,
        skill_id=lesson.skill_id,
        skill_name=lesson.skill_name,
        gap_pct=lesson.gap_pct,
        target_pct=lesson.target_pct,
        what_missing=lesson.what_missing,
        estimated_read_minutes=lesson.estimated_read_minutes,
        generation_status=lesson.generation_status,
        path_generation_seq=lesson.path_generation_seq,
        total_read_seconds=total_secs,
        last_read_at=last_read.isoformat() if last_read else None,
    )


# ── Routes ─────────────────────────────────────────────────────────────────────


@router.post("/practitioners/{practitioner_id}/byte-sized-lessons/generate", status_code=202)
async def generate_byte_sized_lessons(
    practitioner_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> dict:
    """Trigger byte-sized lesson generation for the practitioner's active path.

    **Retry semantics**: if the current max seq has any failed/pending lessons,
    this resets those rows back to 'pending' and reruns — it does NOT create a
    new seq. A new seq is only created when called from learning_paths.generate
    (after a fresh path generation). This prevents spurious history accumulation
    from retry clicks.

    Can also be called standalone for admin recovery.
    """
    enforce_self_or_admin(session, practitioner_id)
    practitioner = await db.get(Practitioner, practitioner_id)
    if practitioner is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")

    # Find active path
    path_result = await db.execute(
        select(LearningPath)
        .where(
            LearningPath.practitioner_id == practitioner_id,
            LearningPath.status == "active",
        )
        .order_by(LearningPath.generated_at.desc())
        .limit(1)
    )
    path = path_result.scalars().first()
    if path is None:
        raise HTTPException(status_code=404, detail="No active learning path found")

    # ── Retry mode: reset failed/pending lessons for the current seq ───────────
    max_seq_result = await db.execute(
        select(sa_func.max(ByteSizedLesson.path_generation_seq)).where(
            ByteSizedLesson.practitioner_id == practitioner_id
        )
    )
    max_seq = max_seq_result.scalar()

    if max_seq is not None:
        # Find failed or pending lessons in the current seq
        retryable_result = await db.execute(
            select(ByteSizedLesson).where(
                ByteSizedLesson.practitioner_id == practitioner_id,
                ByteSizedLesson.path_generation_seq == max_seq,
                ByteSizedLesson.generation_status.in_(["failed", "pending"]),
            )
        )
        retryable = retryable_result.scalars().all()

        if retryable:
            lesson_path_id = retryable[0].learning_path_id
            await db.execute(
                sa_update(ByteSizedLesson)
                .where(
                    ByteSizedLesson.practitioner_id == practitioner_id,
                    ByteSizedLesson.path_generation_seq == max_seq,
                    ByteSizedLesson.generation_status.in_(["failed", "pending"]),
                )
                .values(generation_status="pending")
            )
            await db.commit()

            background_tasks.add_task(
                _generate_byte_sized_lessons,
                practitioner_id,
                lesson_path_id,
                max_seq,
            )

            return {"started": True, "path_generation_seq": max_seq, "retried": True}

    # ── Creation mode: no existing lessons (or all already ready) ──────────────
    new_seq = (max_seq or 0) + 1

    # Fetch path items
    items_result = await db.execute(
        select(LearningPathItem)
        .where(LearningPathItem.learning_path_id == path.id)
        .order_by(LearningPathItem.sequence_order)
    )
    path_items = items_result.scalars().all()

    # Fetch skill names for denormalization
    skill_ids = [pi.skill_id for pi in path_items]
    skills_result = await db.execute(
        select(Skill).where(Skill.id.in_(skill_ids))
    )
    skills_by_id = {s.id: s for s in skills_result.scalars().all()}

    # Fetch mastery for gap_pct
    snapshots_result = await db.execute(
        select(SkillProfileSnapshot).where(
            SkillProfileSnapshot.practitioner_id == practitioner_id,
            SkillProfileSnapshot.skill_id.in_(skill_ids),
        )
    )
    mastery_by_skill = {
        s.skill_id: float(s.mastery_score)
        for s in snapshots_result.scalars().all()
    }

    # Create pending lesson rows
    for pi in path_items:
        skill = skills_by_id.get(pi.skill_id)
        mastery = mastery_by_skill.get(pi.skill_id, 0.0)
        lesson = ByteSizedLesson(
            id=str(uuid.uuid4()),
            practitioner_id=practitioner_id,
            learning_path_id=path.id,
            skill_id=pi.skill_id,
            skill_name=skill.name if skill else pi.skill_id,
            gap_pct=1.0 - mastery,
            target_pct=0.85,
            path_generation_seq=new_seq,
            generation_status="pending",
        )
        db.add(lesson)

    await db.commit()

    background_tasks.add_task(
        _generate_byte_sized_lessons,
        practitioner_id,
        path.id,
        new_seq,
    )

    return {"started": True, "path_generation_seq": new_seq}


@router.get(
    "/practitioners/{practitioner_id}/byte-sized-lessons",
    response_model=LessonListResponse,
)
async def list_byte_sized_lessons(
    practitioner_id: str,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> LessonListResponse:
    """Return lessons grouped: current (latest seq) and history (prior seqs)."""
    enforce_self_or_admin(session, practitioner_id)
    practitioner = await db.get(Practitioner, practitioner_id)
    if practitioner is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")

    lessons_result = await db.execute(
        select(ByteSizedLesson).where(
            ByteSizedLesson.practitioner_id == practitioner_id
        )
    )
    lessons = lessons_result.scalars().all()

    if not lessons:
        return LessonListResponse(current=[], history=[])

    max_seq = max(l.path_generation_seq for l in lessons)

    current_path_id: str | None = next(
        (l.learning_path_id for l in lessons if l.path_generation_seq == max_seq),
        None,
    )

    # Fetch all read sessions for this practitioner's lessons
    lesson_ids = [l.id for l in lessons]
    reads_result = await db.execute(
        select(LessonRead).where(LessonRead.lesson_id.in_(lesson_ids))
    )
    reads_by_lesson: dict[str, list[LessonRead]] = {}
    for r in reads_result.scalars().all():
        reads_by_lesson.setdefault(r.lesson_id, []).append(r)

    current = []
    history = []
    for lesson in sorted(lessons, key=lambda l: (-l.path_generation_seq, -l.gap_pct)):
        summary = _build_lesson_summary(lesson, reads_by_lesson.get(lesson.id, []))
        if lesson.path_generation_seq == max_seq:
            current.append(summary)
        else:
            history.append(summary)

    # Only surface history rows from a genuinely different learning path AND with
    # at least one ready lesson.  Per previous learning_path_id, show only the
    # HIGHEST seq (the most recent generation of that old path) — earlier retry
    # seqs for the same path would otherwise cause every skill to repeat once
    # per retry attempt.
    latest_seq_by_prev_path: dict[str, int] = {}
    for l in lessons:
        if (
            l.path_generation_seq < max_seq
            and l.learning_path_id != current_path_id
            and l.generation_status == "ready"
        ):
            pid = l.learning_path_id
            if pid not in latest_seq_by_prev_path or l.path_generation_seq > latest_seq_by_prev_path[pid]:
                latest_seq_by_prev_path[pid] = l.path_generation_seq

    history_eligible_seqs: set[int] = set(latest_seq_by_prev_path.values())
    history = [s for s in history if s.path_generation_seq in history_eligible_seqs]

    return LessonListResponse(current=current, history=history)


@router.get(
    "/practitioners/{practitioner_id}/byte-sized-lessons/{lesson_id}",
    response_model=LessonDetail,
)
async def get_byte_sized_lesson(
    practitioner_id: str,
    lesson_id: str,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> LessonDetail:
    """Full lesson detail including content_md and external_links."""
    enforce_self_or_admin(session, practitioner_id)
    lesson = await db.get(ByteSizedLesson, lesson_id)
    if lesson is None or lesson.practitioner_id != practitioner_id:
        raise HTTPException(status_code=404, detail="Lesson not found")

    reads_result = await db.execute(
        select(LessonRead).where(LessonRead.lesson_id == lesson_id)
    )
    reads = reads_result.scalars().all()

    summary = _build_lesson_summary(lesson, list(reads))
    return LessonDetail(
        **summary.model_dump(),
        content_md=lesson.content_md,
        external_links=lesson.external_links,
    )


@router.post(
    "/practitioners/{practitioner_id}/byte-sized-lessons/{lesson_id}/read-sessions",
    status_code=201,
    response_model=ReadSessionResponse,
)
async def open_read_session(
    practitioner_id: str,
    lesson_id: str,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> ReadSessionResponse:
    """Open a new read session (modal opened)."""
    enforce_self_or_admin(session, practitioner_id)
    lesson = await db.get(ByteSizedLesson, lesson_id)
    if lesson is None or lesson.practitioner_id != practitioner_id:
        raise HTTPException(status_code=404, detail="Lesson not found")

    now = datetime.now(UTC)
    read = LessonRead(
        id=str(uuid.uuid4()),
        lesson_id=lesson_id,
        practitioner_id=practitioner_id,
        started_at=now,
        duration_seconds=None,
    )
    db.add(read)
    await db.commit()

    return ReadSessionResponse(
        session_id=read.id,
        started_at=now.isoformat(),
    )


@router.patch(
    "/practitioners/{practitioner_id}/byte-sized-lessons/{lesson_id}/read-sessions/{session_id}",
    response_model=dict,
)
async def close_read_session(
    practitioner_id: str,
    lesson_id: str,
    session_id: str,
    body: ReadSessionClose,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> dict:
    """Close a read session (modal closed), recording duration_seconds. Idempotent."""
    enforce_self_or_admin(session, practitioner_id)
    read = await db.get(LessonRead, session_id)
    if read is None or read.lesson_id != lesson_id or read.practitioner_id != practitioner_id:
        raise HTTPException(status_code=404, detail="Read session not found")

    if read.duration_seconds is not None:
        return {"status": "already_closed", "duration_seconds": read.duration_seconds}

    read.duration_seconds = body.duration_seconds
    await db.commit()
    return {"status": "closed", "duration_seconds": read.duration_seconds}
