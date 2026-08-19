"""Mock Exam API — Phase 11.

Routes:
  POST   /practitioners/{id}/mock-exams                        start a new exam session
  GET    /practitioners/{id}/mock-exams/active                 get current active session
  GET    /practitioners/{id}/mock-exams/{session_id}           get a specific session by ID
  PATCH  /practitioners/{id}/mock-exams/{session_id}/pause     pause the timer
  PATCH  /practitioners/{id}/mock-exams/{session_id}/resume    resume the timer
  POST   /practitioners/{id}/mock-exams/{session_id}/answer/{question_id}  answer a question
  POST   /practitioners/{id}/mock-exams/{session_id}/complete  submit the exam
"""

from __future__ import annotations

import logging
import random
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.mock_exam_generator import (
    MockExamGeneratorAgent,
    MockExamGeneratorInput,
    MockExamGeneratorOutput,
    MockExamQuestionSpec,
)
from app.agents.model_client import create_model_client
from app.api.deps.session import SessionInfo, enforce_self_or_admin, require_any_authenticated
from app.db.models import (
    CertificationDomain,
    MockExamQuestion,
    MockExamSession,
    Practitioner,
    PractitionerProfile,
    Skill,
    SkillProfileEvent,
)
from app.db.session import AsyncSessionLocal, get_db

router = APIRouter(tags=["mock_exams"])

_BATCH_SIZE = 15  # questions per generation batch
_bg_log = logging.getLogger(__name__)


# ── Response schemas ──────────────────────────────────────────────────────────

class MockExamQuestionRead(BaseModel):
    id: str
    sequence_order: int
    certification_domain_name: str | None
    skill_name: str | None
    prompt: str
    options: list[str]              # from answer_key.options
    # revealed only after answering
    correct_index: int | None
    trap_index: int | None          # revealed only after answering
    trap_explanation: str | None    # revealed only after answering — shown when trap option chosen
    explanation: str | None         # revealed only after answering — shown when any wrong option chosen
    difficulty: float
    response: dict | None           # {selected_index: N} or null
    score: float | None
    answered_at: str | None
    is_trap_selected: bool          # true when answered response matches trap_index

    @classmethod
    def from_orm(cls, q: MockExamQuestion, *, reveal: bool = False) -> "MockExamQuestionRead":
        answered = q.score is not None
        selected_idx = (q.response or {}).get("selected_index")
        trap_idx = q.answer_key.get("trap_index")
        is_trap = (
            answered
            and selected_idx is not None
            and trap_idx is not None
            and selected_idx == trap_idx
        )
        return cls(
            id=q.id,
            sequence_order=q.sequence_order,
            certification_domain_name=q.certification_domain_name,
            skill_name=q.skill_name,
            prompt=q.prompt,
            options=q.answer_key.get("options", []),
            correct_index=q.answer_key.get("correct_index") if (answered or reveal) else None,
            trap_index=q.answer_key.get("trap_index") if (answered or reveal) else None,
            trap_explanation=q.trap_explanation if (answered or reveal) else None,
            explanation=q.answer_key.get("explanation") if (answered or reveal) else None,
            difficulty=float(q.difficulty or 0.85),
            response=q.response,
            score=float(q.score) if q.score is not None else None,
            answered_at=q.answered_at.isoformat() if q.answered_at else None,
            is_trap_selected=is_trap,
        )


class MockExamSessionRead(BaseModel):
    id: str
    certification_id: str
    certification_code: str
    certification_name: str
    exam_question_count: int
    exam_duration_minutes: int
    exam_passing_score_pct: float
    status: str
    time_elapsed_seconds: int
    score: float | None
    correct_count: int | None
    total_count: int
    started_at: str
    completed_at: str | None
    abandoned_reason: str | None
    abandoned_at: str | None
    questions: list[MockExamQuestionRead]


class MockExamSessionSummary(BaseModel):
    """Lightweight row for the exam history table — no questions payload."""
    id: str
    certification_id: str
    certification_code: str
    certification_name: str
    exam_passing_score_pct: float
    status: str
    score: float | None
    correct_count: int | None
    total_count: int
    answered_count: int
    time_elapsed_seconds: int
    started_at: str
    completed_at: str | None
    abandoned_reason: str | None
    abandoned_at: str | None


class AbandonRequest(BaseModel):
    reason: str


class AnswerRequest(BaseModel):
    selected_index: int


# ── Helpers ───────────────────────────────────────────────────────────────────

def _session_read(
    session: MockExamSession,
    *,
    reveal_all: bool = False,
) -> MockExamSessionRead:
    """Build the read schema from the ORM session, optionally revealing all answers."""
    cert = session.certification
    return MockExamSessionRead(
        id=session.id,
        certification_id=cert.id,
        certification_code=cert.code,
        certification_name=cert.name,
        exam_question_count=cert.exam_question_count or 0,
        exam_duration_minutes=cert.exam_duration_minutes or 0,
        exam_passing_score_pct=float(cert.exam_passing_score_pct or 0),
        status=session.status,
        time_elapsed_seconds=session.time_elapsed_seconds,
        score=float(session.score) if session.score is not None else None,
        correct_count=session.correct_count,
        total_count=session.total_count,
        started_at=session.started_at.isoformat(),
        completed_at=session.completed_at.isoformat() if session.completed_at else None,
        abandoned_reason=session.abandoned_reason,
        abandoned_at=session.abandoned_at.isoformat() if session.abandoned_at else None,
        questions=[
            MockExamQuestionRead.from_orm(q, reveal=reveal_all)
            for q in sorted(session.questions, key=lambda x: x.sequence_order)
        ],
    )


async def _load_session_with_cert(
    session_id: str,
    practitioner_id: str,
    db: AsyncSession,
) -> MockExamSession:
    """Load a MockExamSession with certification and questions eagerly loaded.

    Raises 404 if not found, 403 if it belongs to a different practitioner.
    """
    result = await db.execute(
        select(MockExamSession)
        .options(
            selectinload(MockExamSession.questions),
            selectinload(MockExamSession.certification),
        )
        .where(MockExamSession.id == session_id)
    )
    exam_session = result.scalar_one_or_none()
    if exam_session is None:
        raise HTTPException(status_code=404, detail="Mock exam session not found")
    if exam_session.practitioner_id != practitioner_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return exam_session


def _assign_domain_focus(
    domains_data: list[dict],
    batch_index: int,
    total_batches: int,
) -> str | None:
    """Pick a domain for a given batch by cycling proportionally by weight."""
    if not domains_data:
        return None
    # Build a weighted list: each domain gets floor(total_batches * weight_pct/100) slots,
    # remainder slots go to the heaviest domains.
    expanded: list[str] = []
    for d in domains_data:
        slots = max(1, round(total_batches * float(d["weight_pct"]) / 100))
        expanded.extend([d["name"]] * slots)
    # Trim or pad to exactly total_batches
    while len(expanded) < total_batches:
        expanded.append(domains_data[0]["name"])
    expanded = expanded[:total_batches]
    return expanded[batch_index % len(expanded)]


# ── Question recycling helpers ───────────────────────────────────────────────

async def _pick_recycled_questions(
    practitioner_id: str,
    domain_focus: str | None,
    current_session_id: str,
    slots: int,
    db: "AsyncSession",
) -> list[MockExamQuestion]:
    """Return up to `slots` recycled MockExamQuestion rows for a new exam.

    Priority order (per Phase 19 design):
      (a) Unexercised — unanswered questions from ABANDONED sessions for this domain
      (b) Remediation — incorrectly answered (score=0) questions from ANY prior session

    Questions from the current session being generated are excluded.
    Returns ORM objects only — caller must copy them into new DB rows.
    """
    if slots <= 0:
        return []

    # ── (a) Unexercised pool: abandoned sessions, unanswered, matching domain ──
    unexercised_q = (
        select(MockExamQuestion)
        .join(MockExamSession, MockExamQuestion.session_id == MockExamSession.id)
        .where(
            MockExamSession.practitioner_id == practitioner_id,
            MockExamSession.status == "abandoned",
            MockExamSession.id != current_session_id,
            MockExamQuestion.response.is_(None),
            # domain match: if domain_focus given, filter; else accept any domain
            (
                MockExamQuestion.certification_domain_name == domain_focus
                if domain_focus
                else sa.true()
            ),
        )
        .order_by(MockExamSession.started_at.desc(), sa.func.random())
        .limit(slots)
    )
    unexercised_result = await db.execute(unexercised_q)
    unexercised = list(unexercised_result.scalars().all())

    recycled: list[MockExamQuestion] = list(unexercised)
    remaining = slots - len(recycled)

    if remaining <= 0:
        return recycled

    # ── (b) Remediation pool: score=0 from any prior session (up to 30% of slots) ──
    remedia_cap = max(1, round(slots * 0.3))
    already_ids = {q.id for q in recycled}

    remedia_q = (
        select(MockExamQuestion)
        .join(MockExamSession, MockExamQuestion.session_id == MockExamSession.id)
        .where(
            MockExamSession.practitioner_id == practitioner_id,
            MockExamSession.id != current_session_id,
            MockExamQuestion.score == 0.0,
            MockExamQuestion.id.notin_(already_ids) if already_ids else sa.true(),
            (
                MockExamQuestion.certification_domain_name == domain_focus
                if domain_focus
                else sa.true()
            ),
        )
        .order_by(sa.func.random())
        .limit(min(remaining, remedia_cap))
    )
    remedia_result = await db.execute(remedia_q)
    recycled.extend(remedia_result.scalars().all())

    return recycled


def _copy_question(
    source: MockExamQuestion,
    *,
    session_id: str,
    sequence_order: int,
) -> MockExamQuestion:
    """Copy a question into a new session, re-shuffling its options."""
    options: list[str] = source.answer_key.get("options", [])
    n = len(options)
    perm = list(range(n))
    random.shuffle(perm)
    shuffled_options = [options[j] for j in perm]
    rev = {old: new for new, old in enumerate(perm)}
    orig_correct = source.answer_key.get("correct_index", 0)
    orig_trap = source.answer_key.get("trap_index")
    return MockExamQuestion(
        id=str(uuid.uuid4()),
        session_id=session_id,
        sequence_order=sequence_order,
        certification_domain_name=source.certification_domain_name,
        skill_name=source.skill_name,
        prompt=source.prompt,
        answer_key={
            "options": shuffled_options,
            "correct_index": rev.get(orig_correct, orig_correct),
            "trap_index": rev.get(orig_trap, orig_trap) if orig_trap is not None else None,
            "explanation": source.answer_key.get("explanation"),
        },
        trap_explanation=source.trap_explanation,
        difficulty=float(source.difficulty or 0.85),
        response=None,
        score=None,
        answered_at=None,
    )


# ── Background question generation ───────────────────────────────────────────

async def _generate_exam_questions_bg(
    session_id: str,
    practitioner_id: str,
    cert_id: str,
    batch_sizes: list[int],
    domains_data: list[dict],  # [{id, name, weight_pct}]
) -> None:
    """Background task: generate exam questions domain-by-domain.

    Each batch is committed immediately after generation so the frontend can
    poll and see questions arrive progressively.  The session transitions from
    'generating' → 'in_progress' once all batches complete (or 'failed' if none
    succeed).
    """
    _bg_log.info(
        "mock_exam_bg: started for session=%s batches=%d total_q=%d",
        session_id, len(batch_sizes), sum(batch_sizes),
    )

    model_client = create_model_client()
    total_batches = len(batch_sizes)
    seq_offset = 0

    async with AsyncSessionLocal() as db:
        try:
            from app.db.models import Certification
            cert = await db.get(Certification, cert_id)
            if cert is None:
                raise ValueError(f"Certification {cert_id!r} not found")

            for batch_idx, size in enumerate(batch_sizes):
                domain_focus = _assign_domain_focus(domains_data, batch_idx, total_batches)

                try:
                    # ── Step 1: fill slots from recycled questions ──────────
                    recycled = await _pick_recycled_questions(
                        practitioner_id=practitioner_id,
                        domain_focus=domain_focus,
                        current_session_id=session_id,
                        slots=size,
                        db=db,
                    )
                    copied: list[MockExamQuestion] = []
                    for rec in recycled:
                        copied.append(_copy_question(
                            rec,
                            session_id=session_id,
                            sequence_order=seq_offset + len(copied) + 1,
                        ))
                        db.add(copied[-1])

                    remaining_slots = size - len(copied)
                    _bg_log.info(
                        "mock_exam_bg: batch %d/%d — %d recycled, %d LLM slots",
                        batch_idx + 1, total_batches, len(copied), remaining_slots,
                    )

                    # ── Step 2: call LLM only for remaining slots ───────────
                    llm_specs: list[MockExamQuestionSpec] = []
                    if remaining_slots > 0:
                        agent = MockExamGeneratorAgent(client=model_client, db_session=db)
                        output: MockExamGeneratorOutput = await agent.run(MockExamGeneratorInput(
                            cert_code=cert.code,
                            cert_name=cert.name,
                            batch_size=remaining_slots,
                            domain_focus=domain_focus,
                            batch_number=batch_idx + 1,
                        ))
                        llm_specs = list(output.questions)
                        random.shuffle(llm_specs)

                    # ── Step 3: persist LLM-generated questions ─────────────
                    llm_offset = seq_offset + len(copied)
                    for i, spec in enumerate(llm_specs):
                        n_opts = len(spec.options)
                        perm = list(range(n_opts))
                        random.shuffle(perm)
                        shuffled_options = [spec.options[j] for j in perm]
                        rev = {old: new for new, old in enumerate(perm)}
                        new_correct = rev.get(spec.correct_index, spec.correct_index)
                        new_trap = (
                            rev.get(spec.trap_index, spec.trap_index)
                            if spec.trap_index is not None
                            else None
                        )
                        question = MockExamQuestion(
                            id=str(uuid.uuid4()),
                            session_id=session_id,
                            sequence_order=llm_offset + i + 1,
                            certification_domain_name=spec.certification_domain_name,
                            skill_name=spec.skill_name,
                            prompt=spec.prompt,
                            answer_key={
                                "options": shuffled_options,
                                "correct_index": new_correct,
                                "trap_index": new_trap,
                                "explanation": spec.explanation,
                            },
                            trap_explanation=spec.trap_explanation,
                            difficulty=round(float(spec.difficulty or 0.85), 3),
                        )
                        db.add(question)

                    batch_count = len(copied) + len(llm_specs)
                    await db.commit()  # commit this domain's batch — frontend can now see these questions
                    seq_offset += batch_count
                    _bg_log.info(
                        "mock_exam_bg: batch %d/%d done — %d questions (%d recycled + %d new, running total=%d)",
                        batch_idx + 1, total_batches, batch_count, len(copied), len(llm_specs), seq_offset,
                    )

                except Exception as exc:
                    _bg_log.warning(
                        "mock_exam_bg: batch %d/%d failed: %s",
                        batch_idx + 1, total_batches, exc, exc_info=True,
                    )
                    # Continue — partial exam is still usable

            # Transition session to in_progress (or failed if nothing generated)
            now = datetime.now(UTC)
            session_obj = await db.get(MockExamSession, session_id)
            if session_obj is not None:
                if seq_offset == 0:
                    session_obj.status = "failed"
                    _bg_log.error(
                        "mock_exam_bg: all batches failed — session=%s marked failed", session_id
                    )
                else:
                    session_obj.status = "in_progress"
                    session_obj.last_resumed_at = now
                    session_obj.total_count = seq_offset
                    _bg_log.info(
                        "mock_exam_bg: session=%s in_progress with %d questions",
                        session_id, seq_offset,
                    )
                await db.commit()

        except Exception as top_exc:
            _bg_log.error(
                "mock_exam_bg: fatal error for session=%s: %s", session_id, top_exc, exc_info=True
            )
            # Best-effort mark as failed in a fresh session
            try:
                async with AsyncSessionLocal() as err_db:
                    session_obj = await err_db.get(MockExamSession, session_id)
                    if session_obj is not None:
                        session_obj.status = "failed"
                        await err_db.commit()
            except Exception:
                pass


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/practitioners/{practitioner_id}/mock-exams",
    response_model=MockExamSessionRead,
    status_code=202,
)
async def start_mock_exam(
    practitioner_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    session_info: SessionInfo = Depends(require_any_authenticated),
) -> MockExamSessionRead:
    """Start a new mock exam session.

    Returns 202 immediately with a 'generating' session.  Questions are
    generated per exam domain in a background task and committed incrementally;
    poll GET /mock-exams/{session_id} until status becomes 'in_progress'.
    """
    enforce_self_or_admin(session_info, practitioner_id)

    practitioner = await db.get(Practitioner, practitioner_id)
    if practitioner is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")

    # Reject if a session is already in flight (generating, in_progress, or paused)
    active_result = await db.execute(
        select(MockExamSession).where(
            MockExamSession.practitioner_id == practitioner_id,
            MockExamSession.status.in_(["generating", "in_progress", "paused"]),
        )
    )
    existing = active_result.scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"An active mock exam session already exists (id={existing.id!r}, "
                f"status={existing.status!r}). Pause or complete it before starting a new one."
            ),
        )

    # Get active profile → certification_id
    profile_result = await db.execute(
        select(PractitionerProfile).where(
            PractitionerProfile.practitioner_id == practitioner_id,
            PractitionerProfile.is_active == True,  # noqa: E712
        )
    )
    profile = profile_result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(
            status_code=400,
            detail="No active profile found. Activate a profile before starting a mock exam.",
        )
    if not profile.certification_id:
        raise HTTPException(
            status_code=400,
            detail="Active profile has no associated certification.",
        )

    # Load certification
    from app.db.models import Certification
    cert = await db.get(Certification, profile.certification_id)
    if cert is None:
        raise HTTPException(status_code=404, detail="Certification not found")
    if not cert.exam_question_count or not cert.exam_duration_minutes:
        raise HTTPException(
            status_code=400,
            detail=f"Certification {cert.code!r} has no exam configuration (question count / duration).",
        )

    # Load domains ordered by sequence_order
    domains_result = await db.execute(
        select(CertificationDomain)
        .where(CertificationDomain.certification_id == cert.id)
        .order_by(CertificationDomain.sequence_order)
    )
    domains: list[CertificationDomain] = list(domains_result.scalars().all())
    # Serialize to plain dicts so the background task can use them safely
    domains_data = [
        {"id": d.id, "name": d.domain_name, "weight_pct": float(d.weight_pct or 0)}
        for d in domains
    ]

    # Compute batch sizes
    total_questions = cert.exam_question_count
    full_batches, remainder = divmod(total_questions, _BATCH_SIZE)
    batch_sizes: list[int] = [_BATCH_SIZE] * full_batches
    if remainder:
        batch_sizes.append(remainder)

    now = datetime.now(UTC)

    # Create session immediately with status="generating"
    exam_session = MockExamSession(
        id=str(uuid.uuid4()),
        practitioner_id=practitioner_id,
        certification_id=cert.id,
        status="generating",
        time_elapsed_seconds=0,
        last_resumed_at=None,
        total_count=cert.exam_question_count,
        started_at=now,
        created_at=now,
    )
    db.add(exam_session)
    await db.flush()  # get session.id

    # Reload with relationships so _session_read can build the response
    result = await db.execute(
        select(MockExamSession)
        .options(
            selectinload(MockExamSession.questions),
            selectinload(MockExamSession.certification),
        )
        .where(MockExamSession.id == exam_session.id)
    )
    loaded = result.scalar_one()
    response_data = _session_read(loaded, reveal_all=False)

    await db.commit()

    # Kick off background generation AFTER commit so the session row is visible
    background_tasks.add_task(
        _generate_exam_questions_bg,
        exam_session.id,
        practitioner_id,
        cert.id,
        batch_sizes,
        domains_data,
    )

    _bg_log.info(
        "mock_exam: session=%s created (generating), batches=%d total_q=%d",
        exam_session.id, len(batch_sizes), total_questions,
    )

    return response_data


@router.get(
    "/practitioners/{practitioner_id}/mock-exams/active",
    response_model=MockExamSessionRead,
)
async def get_active_mock_exam(
    practitioner_id: str,
    db: AsyncSession = Depends(get_db),
    session_info: SessionInfo = Depends(require_any_authenticated),
) -> MockExamSessionRead:
    """Return the single generating/in_progress/paused session for this practitioner."""
    enforce_self_or_admin(session_info, practitioner_id)

    practitioner = await db.get(Practitioner, practitioner_id)
    if practitioner is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")

    result = await db.execute(
        select(MockExamSession)
        .options(
            selectinload(MockExamSession.questions),
            selectinload(MockExamSession.certification),
        )
        .where(
            MockExamSession.practitioner_id == practitioner_id,
            MockExamSession.status.in_(["generating", "in_progress", "paused"]),
        )
    )
    exam_session = result.scalar_one_or_none()
    if exam_session is None:
        raise HTTPException(status_code=404, detail="No active mock exam session found")

    return _session_read(exam_session, reveal_all=False)


@router.get(
    "/practitioners/{practitioner_id}/mock-exams/{session_id}",
    response_model=MockExamSessionRead,
)
async def get_mock_exam_session(
    practitioner_id: str,
    session_id: str,
    db: AsyncSession = Depends(get_db),
    session_info: SessionInfo = Depends(require_any_authenticated),
) -> MockExamSessionRead:
    """Fetch a specific mock exam session by ID.

    Returns the session regardless of status — callers should poll until
    status transitions from 'generating' to 'in_progress'.
    """
    enforce_self_or_admin(session_info, practitioner_id)

    exam_session = await _load_session_with_cert(session_id, practitioner_id, db)
    return _session_read(exam_session, reveal_all=exam_session.status == "completed")


@router.patch(
    "/practitioners/{practitioner_id}/mock-exams/{session_id}/pause",
    response_model=MockExamSessionRead,
)
async def pause_mock_exam(
    practitioner_id: str,
    session_id: str,
    db: AsyncSession = Depends(get_db),
    session_info: SessionInfo = Depends(require_any_authenticated),
) -> MockExamSessionRead:
    """Pause the exam timer. Accumulates elapsed seconds into time_elapsed_seconds."""
    enforce_self_or_admin(session_info, practitioner_id)

    exam_session = await _load_session_with_cert(session_id, practitioner_id, db)
    if exam_session.status != "in_progress":
        raise HTTPException(
            status_code=400,
            detail=f"Session is {exam_session.status!r}, not in_progress — cannot pause.",
        )

    now = datetime.now(UTC)
    if exam_session.last_resumed_at is not None:
        elapsed = int((now - exam_session.last_resumed_at).total_seconds())
        exam_session.time_elapsed_seconds = (exam_session.time_elapsed_seconds or 0) + elapsed

    exam_session.status = "paused"
    exam_session.last_resumed_at = None
    await db.commit()
    await db.refresh(exam_session)

    return _session_read(exam_session, reveal_all=False)


@router.patch(
    "/practitioners/{practitioner_id}/mock-exams/{session_id}/resume",
    response_model=MockExamSessionRead,
)
async def resume_mock_exam(
    practitioner_id: str,
    session_id: str,
    db: AsyncSession = Depends(get_db),
    session_info: SessionInfo = Depends(require_any_authenticated),
) -> MockExamSessionRead:
    """Resume a paused exam, setting last_resumed_at to now."""
    enforce_self_or_admin(session_info, practitioner_id)

    exam_session = await _load_session_with_cert(session_id, practitioner_id, db)
    if exam_session.status != "paused":
        raise HTTPException(
            status_code=400,
            detail=f"Session is {exam_session.status!r}, not paused — cannot resume.",
        )

    exam_session.status = "in_progress"
    exam_session.last_resumed_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(exam_session)

    return _session_read(exam_session, reveal_all=False)


@router.post(
    "/practitioners/{practitioner_id}/mock-exams/{session_id}/answer/{question_id}",
    response_model=MockExamQuestionRead,
)
async def answer_question(
    practitioner_id: str,
    session_id: str,
    question_id: str,
    body: AnswerRequest,
    db: AsyncSession = Depends(get_db),
    session_info: SessionInfo = Depends(require_any_authenticated),
) -> MockExamQuestionRead:
    """Submit an answer for a question. Returns the question with correct_index revealed."""
    enforce_self_or_admin(session_info, practitioner_id)

    exam_session = await _load_session_with_cert(session_id, practitioner_id, db)
    if exam_session.status != "in_progress":
        raise HTTPException(
            status_code=400,
            detail=f"Session is {exam_session.status!r} — answers can only be submitted to an in_progress session.",
        )

    # Find the question
    question = next(
        (q for q in exam_session.questions if q.id == question_id),
        None,
    )
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found in this session")
    if question.score is not None:
        raise HTTPException(status_code=409, detail="Question already answered")

    # Validate selected_index
    options = question.answer_key.get("options", [])
    if body.selected_index < 0 or body.selected_index >= len(options):
        raise HTTPException(
            status_code=400,
            detail=f"selected_index {body.selected_index} is out of range (0–{len(options) - 1})",
        )

    # Grade: MCQ is binary
    correct_index: int = question.answer_key["correct_index"]
    score = 1.0 if body.selected_index == correct_index else 0.0

    question.response = {"selected_index": body.selected_index}
    question.score = score
    question.answered_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(question)

    # Return with correct_index and trap revealed (answered=True)
    return MockExamQuestionRead.from_orm(question, reveal=True)


@router.post(
    "/practitioners/{practitioner_id}/mock-exams/{session_id}/complete",
    response_model=MockExamSessionRead,
)
async def complete_mock_exam(
    practitioner_id: str,
    session_id: str,
    db: AsyncSession = Depends(get_db),
    session_info: SessionInfo = Depends(require_any_authenticated),
) -> MockExamSessionRead:
    """Submit and score the exam. All questions must be answered first.

    Also writes SkillProfileEvent rows (source='mock_exam') for each unique skill_name
    so that exam performance feeds into adoption trend tracking.
    """
    enforce_self_or_admin(session_info, practitioner_id)

    exam_session = await _load_session_with_cert(session_id, practitioner_id, db)
    if exam_session.status == "completed":
        raise HTTPException(status_code=400, detail="Session is already completed")

    # Require all questions answered
    unanswered = [q for q in exam_session.questions if q.score is None]
    if unanswered:
        raise HTTPException(
            status_code=400,
            detail=(
                f"{len(unanswered)} question(s) still unanswered. "
                "Answer all questions before completing the exam."
            ),
        )

    # Compute totals
    correct_count = sum(1 for q in exam_session.questions if q.score and float(q.score) >= 1.0)
    total_count = len(exam_session.questions)
    overall_score = correct_count / total_count if total_count else 0.0

    now = datetime.now(UTC)
    exam_session.status = "completed"
    exam_session.completed_at = now
    exam_session.score = round(overall_score, 3)
    exam_session.correct_count = correct_count
    exam_session.total_count = total_count

    cert = exam_session.certification

    # Write SkillProfileEvent rows for each unique skill_name
    skill_names_seen: set[str] = set()
    for q in exam_session.questions:
        if not q.skill_name:
            continue
        if q.skill_name in skill_names_seen:
            continue
        skill_names_seen.add(q.skill_name)

        # Look up skill_id by name
        skill_result = await db.execute(
            select(Skill).where(Skill.name == q.skill_name)
        )
        skill = skill_result.scalar_one_or_none()
        if skill is None:
            continue  # skip if skill not in graph

        db.add(SkillProfileEvent(
            id=str(uuid.uuid4()),
            practitioner_id=practitioner_id,
            skill_id=skill.id,
            source="mock_exam",
            signal_strength=round(overall_score, 3),
            occurred_at=now,
            metadata_={
                "exam_session_id": exam_session.id,
                "cert_code": cert.code,
                "score": overall_score,
                "correct": correct_count,
                "total": total_count,
            },
        ))

    await db.commit()

    # Reload fully for response (all answers now revealed)
    result = await db.execute(
        select(MockExamSession)
        .options(
            selectinload(MockExamSession.questions),
            selectinload(MockExamSession.certification),
        )
        .where(MockExamSession.id == exam_session.id)
    )
    loaded = result.scalar_one()
    return _session_read(loaded, reveal_all=True)


@router.post(
    "/practitioners/{practitioner_id}/mock-exams/{session_id}/abandon",
    response_model=MockExamSessionRead,
)
async def abandon_mock_exam(
    practitioner_id: str,
    session_id: str,
    body: AbandonRequest,
    db: AsyncSession = Depends(get_db),
    session_info: SessionInfo = Depends(require_any_authenticated),
) -> MockExamSessionRead:
    """Abandon an active mock exam session.

    Requires a non-empty reason string. The session is marked 'abandoned' so its
    unanswered questions can be recycled into a future exam. A new exam can be
    started immediately after abandoning.
    """
    enforce_self_or_admin(session_info, practitioner_id)

    if not body.reason or not body.reason.strip():
        raise HTTPException(status_code=400, detail="A non-empty abandonment reason is required.")

    exam_session = await _load_session_with_cert(session_id, practitioner_id, db)

    if exam_session.status in ("completed", "abandoned", "failed"):
        raise HTTPException(
            status_code=400,
            detail=f"Session is already {exam_session.status!r} — cannot abandon.",
        )

    now = datetime.now(UTC)

    # Accumulate any un-paused elapsed time before abandoning
    if exam_session.status == "in_progress" and exam_session.last_resumed_at is not None:
        elapsed = int((now - exam_session.last_resumed_at).total_seconds())
        exam_session.time_elapsed_seconds = (exam_session.time_elapsed_seconds or 0) + elapsed

    exam_session.status = "abandoned"
    exam_session.abandoned_reason = body.reason.strip()
    exam_session.abandoned_at = now
    exam_session.last_resumed_at = None

    await db.commit()
    await db.refresh(exam_session)

    return _session_read(exam_session, reveal_all=False)


@router.get(
    "/practitioners/{practitioner_id}/mock-exams",
    response_model=list[MockExamSessionSummary],
)
async def list_mock_exams(
    practitioner_id: str,
    db: AsyncSession = Depends(get_db),
    session_info: SessionInfo = Depends(require_any_authenticated),
) -> list[MockExamSessionSummary]:
    """Return all mock exam sessions for a practitioner, newest first.

    Returns lightweight summary rows (no questions payload) for the history table.
    """
    enforce_self_or_admin(session_info, practitioner_id)

    practitioner = await db.get(Practitioner, practitioner_id)
    if practitioner is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")

    result = await db.execute(
        select(MockExamSession)
        .options(
            selectinload(MockExamSession.questions),
            selectinload(MockExamSession.certification),
        )
        .where(MockExamSession.practitioner_id == practitioner_id)
        .order_by(MockExamSession.started_at.desc())
    )
    sessions = result.scalars().all()

    summaries: list[MockExamSessionSummary] = []
    for s in sessions:
        cert = s.certification
        answered = sum(1 for q in s.questions if q.response is not None)
        summaries.append(MockExamSessionSummary(
            id=s.id,
            certification_id=cert.id,
            certification_code=cert.code,
            certification_name=cert.name,
            exam_passing_score_pct=float(cert.exam_passing_score_pct or 0),
            status=s.status,
            score=float(s.score) if s.score is not None else None,
            correct_count=s.correct_count,
            total_count=s.total_count,
            answered_count=answered,
            time_elapsed_seconds=s.time_elapsed_seconds or 0,
            started_at=s.started_at.isoformat(),
            completed_at=s.completed_at.isoformat() if s.completed_at else None,
            abandoned_reason=s.abandoned_reason,
            abandoned_at=s.abandoned_at.isoformat() if s.abandoned_at else None,
        ))

    return summaries
