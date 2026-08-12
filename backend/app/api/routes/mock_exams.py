"""Mock Exam API — Phase 11.

Routes:
  POST   /practitioners/{id}/mock-exams                        start a new exam session
  GET    /practitioners/{id}/mock-exams/active                 get current active session
  PATCH  /practitioners/{id}/mock-exams/{session_id}/pause     pause the timer
  PATCH  /practitioners/{id}/mock-exams/{session_id}/resume    resume the timer
  POST   /practitioners/{id}/mock-exams/{session_id}/answer/{question_id}  answer a question
  POST   /practitioners/{id}/mock-exams/{session_id}/complete  submit the exam
"""

from __future__ import annotations

import asyncio
import random
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
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
from app.db.session import get_db

router = APIRouter(tags=["mock_exams"])

_BATCH_SIZE = 15  # questions per generation batch


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
    trap_explanation: str | None    # revealed only after answering
    difficulty: float
    response: dict | None           # {selected_index: N} or null
    score: float | None
    answered_at: str | None

    @classmethod
    def from_orm(cls, q: MockExamQuestion, *, reveal: bool = False) -> "MockExamQuestionRead":
        answered = q.score is not None
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
            difficulty=float(q.difficulty),
            response=q.response,
            score=float(q.score) if q.score is not None else None,
            answered_at=q.answered_at.isoformat() if q.answered_at else None,
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
    questions: list[MockExamQuestionRead]


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
    domains: list[CertificationDomain],
    batch_index: int,
    total_batches: int,
) -> str | None:
    """Pick a domain for a given batch by cycling proportionally by weight."""
    if not domains:
        return None
    # Build a weighted list: each domain gets floor(total_batches * weight_pct/100) slots,
    # remainder slots go to the heaviest domains.
    expanded: list[str] = []
    for d in domains:
        slots = max(1, round(total_batches * float(d.weight_pct) / 100))
        expanded.extend([d.domain_name] * slots)
    # Trim or pad to exactly total_batches
    while len(expanded) < total_batches:
        expanded.append(domains[0].domain_name)
    expanded = expanded[:total_batches]
    return expanded[batch_index % len(expanded)]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/practitioners/{practitioner_id}/mock-exams",
    response_model=MockExamSessionRead,
    status_code=201,
)
async def start_mock_exam(
    practitioner_id: str,
    db: AsyncSession = Depends(get_db),
    session_info: SessionInfo = Depends(require_any_authenticated),
) -> MockExamSessionRead:
    """Start a new mock exam session for the practitioner.

    Rejects if an in_progress or paused session already exists.
    Generates all questions concurrently via asyncio.gather.
    """
    enforce_self_or_admin(session_info, practitioner_id)

    practitioner = await db.get(Practitioner, practitioner_id)
    if practitioner is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")

    # Check for existing active session
    active_result = await db.execute(
        select(MockExamSession).where(
            MockExamSession.practitioner_id == practitioner_id,
            MockExamSession.status.in_(["in_progress", "paused"]),
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

    # Divide into batches
    total_questions = cert.exam_question_count
    full_batches, remainder = divmod(total_questions, _BATCH_SIZE)
    batch_sizes: list[int] = [_BATCH_SIZE] * full_batches
    if remainder:
        batch_sizes.append(remainder)
    total_batches = len(batch_sizes)

    # Build inputs for each batch
    model_client = create_model_client()

    async def _run_batch(batch_idx: int, size: int) -> MockExamGeneratorOutput:
        domain_focus = _assign_domain_focus(domains, batch_idx, total_batches)
        agent = MockExamGeneratorAgent(client=model_client, db_session=db)
        return await agent.run(MockExamGeneratorInput(
            cert_code=cert.code,
            cert_name=cert.name,
            batch_size=size,
            domain_focus=domain_focus,
            batch_number=batch_idx + 1,
        ))

    # Run all batches concurrently
    batch_outputs: list[MockExamGeneratorOutput] = await asyncio.gather(
        *[_run_batch(i, sz) for i, sz in enumerate(batch_sizes)]
    )

    # Flatten all question specs
    all_specs: list[MockExamQuestionSpec] = []
    for out in batch_outputs:
        all_specs.extend(out.questions)

    # Shuffle for randomised order
    random.shuffle(all_specs)

    now = datetime.now(UTC)

    # Create session
    exam_session = MockExamSession(
        id=str(uuid.uuid4()),
        practitioner_id=practitioner_id,
        certification_id=cert.id,
        status="in_progress",
        time_elapsed_seconds=0,
        last_resumed_at=now,
        total_count=len(all_specs),
        started_at=now,
        created_at=now,
    )
    db.add(exam_session)
    await db.flush()  # get session.id

    # Create question rows
    for seq, spec in enumerate(all_specs, start=1):
        question = MockExamQuestion(
            id=str(uuid.uuid4()),
            session_id=exam_session.id,
            sequence_order=seq,
            certification_domain_name=spec.certification_domain_name,
            skill_name=spec.skill_name,
            prompt=spec.prompt,
            answer_key={
                "options": spec.options,
                "correct_index": spec.correct_index,
                "trap_index": spec.trap_index,
            },
            trap_explanation=spec.trap_explanation,
            difficulty=round(spec.difficulty, 3),
        )
        db.add(question)

    await db.commit()

    # Reload with all relationships for response
    result = await db.execute(
        select(MockExamSession)
        .options(
            selectinload(MockExamSession.questions),
            selectinload(MockExamSession.certification),
        )
        .where(MockExamSession.id == exam_session.id)
    )
    loaded = result.scalar_one()
    # Note: correct_index is NOT revealed in the response — only revealed after answering
    return _session_read(loaded, reveal_all=False)


@router.get(
    "/practitioners/{practitioner_id}/mock-exams/active",
    response_model=MockExamSessionRead,
)
async def get_active_mock_exam(
    practitioner_id: str,
    db: AsyncSession = Depends(get_db),
    session_info: SessionInfo = Depends(require_any_authenticated),
) -> MockExamSessionRead:
    """Return the single in_progress or paused session for this practitioner."""
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
            MockExamSession.status.in_(["in_progress", "paused"]),
        )
    )
    exam_session = result.scalar_one_or_none()
    if exam_session is None:
        raise HTTPException(status_code=404, detail="No active mock exam session found")

    return _session_read(exam_session, reveal_all=False)


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
