"""Smart Nudge Campaign API routes — Phase 7.1 / 7.3.

New routes (admin-driven campaign flow):
  GET  /nudges/generate-categories            generate + persist nudge categories
  GET  /nudges/categories                     list recent categories
  POST /nudges/categories/{id}/preview-recipients  resolve matching practitioners
  POST /nudges/categories/{id}/compose        compose message preview (no DB write)
  POST /nudges/send                           bulk-create nudge rows + trigger email
  GET  /nudges/sent                           sent campaign history

Practitioner routes:
  GET  /practitioners/{id}/nudges             practitioner inbox
  PATCH /nudges/{id}/read                     mark read
  GET  /practitioners/{id}/nudges/unread-count  polling endpoint

Mastery history:
  GET  /practitioners/{id}/mastery-history    time-series mastery data
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import ModelClient
from app.agents.model_client import create_model_client
from app.api.deps.session import (
    SessionInfo,
    enforce_self_or_admin,
    require_admin,
    require_admin_or_leadership,
    require_any_authenticated,
)
from app.config import settings
from app.db.models import (
    Attempt,
    Certification,
    CorrelationSnapshot,
    Item,
    MasteryHistory,
    Nudge,
    NudgeCategory,
    Practitioner,
    PractitionerProfile,
    Skill,
    SkillProfileSnapshot,
    WorkflowRun,
)
from app.db.session import get_db
from app.schemas.nudge_campaign import (
    AdoptionTrendsResponse,
    ComposePreviewResponse,
    MasteryHistoryPoint,
    MasteryHistoryResponse,
    NudgeCategoryRead,
    NudgeMarkReadResponse,
    NudgeReadExtended,
    PreviewRecipientsResponse,
    RecipientPreview,
    SendNudgesRequest,
    SendNudgesResponse,
    SentCampaignSummary,
    SkillAdoptionTrend,
    SkillQuizPeriod,
    UnreadCountResponse,
)
from app.services.nudge_resolver import resolve_recipients

router = APIRouter(tags=["nudges"])


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _get_aggregate_kpi(db: AsyncSession) -> dict[str, Any]:
    """Build aggregate-only KPI dict for the NudgeCategoryGenerator agent. No PII."""
    now = datetime.now(UTC)
    cutoff_7d = now - timedelta(days=7)
    cutoff_14d = now - timedelta(days=14)

    total_result = await db.execute(select(func.count()).select_from(Practitioner))
    total = total_result.scalar() or 0

    # No quiz in 7d
    active_7d_result = await db.execute(
        select(Attempt.practitioner_id).where(Attempt.attempted_at >= cutoff_7d).distinct()
    )
    active_7d_ids = {row[0] for row in active_7d_result}
    no_quiz_7d = max(0, total - len(active_7d_ids))

    # No quiz in 14d
    active_14d_result = await db.execute(
        select(Attempt.practitioner_id).where(Attempt.attempted_at >= cutoff_14d).distinct()
    )
    active_14d_ids = {row[0] for row in active_14d_result}
    no_quiz_14d = max(0, total - len(active_14d_ids))

    # No active profile
    active_profile_result = await db.execute(
        select(PractitionerProfile.practitioner_id).where(PractitionerProfile.is_active.is_(True)).distinct()
    )
    with_profile_ids = {row[0] for row in active_profile_result}
    no_profile = max(0, total - len(with_profile_ids))

    # Profile but no skill assessments — simplified
    profile_unrated = 0

    # Skill gap summary: top 5 skills by avg gap from correlation snapshots
    gap_result = await db.execute(
        select(
            CorrelationSnapshot.skill_id,
            func.avg(CorrelationSnapshot.gap_score).label("avg_gap"),
            func.count(CorrelationSnapshot.practitioner_id.distinct()).label("pcount"),
        )
        .where(CorrelationSnapshot.has_adoption_gap.is_(True))
        .group_by(CorrelationSnapshot.skill_id)
        .order_by(func.avg(CorrelationSnapshot.gap_score).desc())
        .limit(5)
    )
    skill_ids_in_gap = []
    skill_gap_rows = []
    for row in gap_result:
        skill_ids_in_gap.append(row.skill_id)
        skill_gap_rows.append((row.skill_id, float(row.avg_gap), row.pcount))

    # Fetch skill names
    skill_names: dict[str, str] = {}
    if skill_ids_in_gap:
        sn_result = await db.execute(select(Skill).where(Skill.id.in_(skill_ids_in_gap)))
        for skill in sn_result.scalars():
            skill_names[skill.id] = skill.name

    skill_gap_summary = [
        {"skill_name": skill_names.get(sid, sid), "avg_gap_score": round(avg, 3), "practitioner_count": pc}
        for sid, avg, pc in skill_gap_rows
    ]

    # Stalled: mastery unchanged in 14d — simplified
    stalled = 0

    # Near cert ready (mastery avg >= 80%)
    near_ready_result = await db.execute(
        select(SkillProfileSnapshot.practitioner_id, func.avg(SkillProfileSnapshot.mastery_score).label("avg"))
        .group_by(SkillProfileSnapshot.practitioner_id)
        .having(func.avg(SkillProfileSnapshot.mastery_score) >= 0.8)
    )
    near_ready_count = len(near_ready_result.all())

    # Nudges sent last 7d
    nudges_7d_result = await db.execute(
        select(func.count()).select_from(Nudge).where(
            Nudge.status == "sent", Nudge.sent_at >= cutoff_7d
        )
    )
    nudges_7d = nudges_7d_result.scalar() or 0

    return {
        "total_practitioners": total,
        "practitioners_no_quiz_7d": no_quiz_7d,
        "practitioners_no_quiz_14d": no_quiz_14d,
        "practitioners_no_profile": no_profile,
        "practitioners_profile_unrated": profile_unrated,
        "skill_gap_summary": skill_gap_summary,
        "practitioners_stalled": stalled,
        "practitioners_near_cert_ready": near_ready_count,
        "nudges_sent_last_7d": nudges_7d,
    }


async def _recipient_to_preview(p: Practitioner, db: AsyncSession) -> RecipientPreview:
    """Build a RecipientPreview for a practitioner."""
    profile_result = await db.execute(
        select(PractitionerProfile).where(
            PractitionerProfile.practitioner_id == p.id,
            PractitionerProfile.is_active.is_(True),
        )
    )
    active_profile = profile_result.scalar_one_or_none()
    cert_code = ""
    if active_profile and active_profile.certification_id:
        cert = await db.get(Certification, active_profile.certification_id)
        cert_code = cert.code if cert else ""
    summary = " · ".join(filter(None, [cert_code, active_profile.name if active_profile else None]))
    return RecipientPreview(
        id=p.id,
        name=p.name,
        email=p.email,
        action_profile_summary=summary or "No active profile",
    )


# ── Category generation ────────────────────────────────────────────────────────

@router.get("/nudges/generate-categories", response_model=list[NudgeCategoryRead])
async def generate_nudge_categories(
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_admin),
) -> list[NudgeCategoryRead]:
    """Generate up to 10 nudge categories from aggregate KPI data. Admin only."""
    from app.agents.nudge_category_generator import NudgeCategoryGeneratorAgent
    from app.schemas.nudge_campaign import NudgeCategoryInput, SkillGapSummaryItem

    kpi = await _get_aggregate_kpi(db)
    agent_input = NudgeCategoryInput(
        total_practitioners=kpi["total_practitioners"],
        practitioners_no_quiz_7d=kpi["practitioners_no_quiz_7d"],
        practitioners_no_quiz_14d=kpi["practitioners_no_quiz_14d"],
        practitioners_no_profile=kpi["practitioners_no_profile"],
        practitioners_profile_unrated=kpi["practitioners_profile_unrated"],
        skill_gap_summary=[SkillGapSummaryItem(**g) for g in kpi["skill_gap_summary"]],
        practitioners_stalled=kpi["practitioners_stalled"],
        practitioners_near_cert_ready=kpi["practitioners_near_cert_ready"],
        nudges_sent_last_7d=kpi["nudges_sent_last_7d"],
    )

    model_client = create_model_client()
    agent = NudgeCategoryGeneratorAgent(client=model_client, db_session=db)
    output = await agent.run(agent_input)

    # Persist categories
    admin_id = session.admin_user_id
    created: list[NudgeCategory] = []
    for cat in output.categories:
        row = NudgeCategory(
            id=str(uuid.uuid4()),
            title=cat.title,
            description=cat.description,
            criteria=cat.criteria,
            is_custom=False,
            tone_hint=cat.tone_hint,
            estimated_reach=cat.estimated_reach,
            created_by_admin_id=admin_id,
        )
        db.add(row)
        created.append(row)
    await db.commit()
    for row in created:
        await db.refresh(row)

    return [NudgeCategoryRead.model_validate(r) for r in created]


@router.get("/nudges/categories", response_model=list[NudgeCategoryRead])
async def list_nudge_categories(
    db: AsyncSession = Depends(get_db),
    _session: SessionInfo = Depends(require_admin_or_leadership),
) -> list[NudgeCategoryRead]:
    """List recent nudge categories. Admin or leadership."""
    result = await db.execute(
        select(NudgeCategory).order_by(NudgeCategory.created_at.desc()).limit(50)
    )
    cats = result.scalars().all()
    return [NudgeCategoryRead.model_validate(c) for c in cats]


@router.post("/nudges/categories/{category_id}/preview-recipients", response_model=PreviewRecipientsResponse)
async def preview_recipients(
    category_id: str,
    db: AsyncSession = Depends(get_db),
    _session: SessionInfo = Depends(require_admin),
) -> PreviewRecipientsResponse:
    """Resolve practitioners matching a category's criteria. Admin only."""
    cat = await db.get(NudgeCategory, category_id)
    if cat is None:
        raise HTTPException(status_code=404, detail="Nudge category not found")

    practitioners_list = await resolve_recipients(cat.criteria, db)
    previews = [await _recipient_to_preview(p, db) for p in practitioners_list]
    return PreviewRecipientsResponse(recipients=previews, total=len(previews))


@router.post("/nudges/categories/{category_id}/compose", response_model=ComposePreviewResponse)
async def compose_campaign_preview(
    category_id: str,
    db: AsyncSession = Depends(get_db),
    _session: SessionInfo = Depends(require_admin),
) -> ComposePreviewResponse:
    """Compose a nudge message preview for a category. No DB writes. Admin only."""
    from app.agents.nudge_campaign_composer import NudgeCampaignComposerAgent
    from app.schemas.nudge_campaign import NudgeCampaignComposerInput

    cat = await db.get(NudgeCategory, category_id)
    if cat is None:
        raise HTTPException(status_code=404, detail="Nudge category not found")

    practitioners_list = await resolve_recipients(cat.criteria, db)
    previews = [await _recipient_to_preview(p, db) for p in practitioners_list]

    agent_input = NudgeCampaignComposerInput(
        category_description=cat.description,
        tone_hint=cat.tone_hint or "warm and encouraging",
        recipient_count=len(practitioners_list),
    )
    model_client = create_model_client()
    agent = NudgeCampaignComposerAgent(client=model_client, db_session=db)
    output = await agent.run(agent_input)

    return ComposePreviewResponse(
        subject=output.subject,
        body=output.body,
        tone_check=output.tone_check,
        recipients=previews,
    )


@router.post("/nudges/send", response_model=SendNudgesResponse)
async def send_nudges(
    body: SendNudgesRequest,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_admin),
) -> SendNudgesResponse:
    """Create nudge rows for selected practitioners and trigger email. Admin only."""
    cat = await db.get(NudgeCategory, body.category_id)
    if cat is None:
        raise HTTPException(status_code=404, detail="Nudge category not found")

    all_recipients = await resolve_recipients(cat.criteria, db)

    # Apply overrides
    excluded_ids: set[str] = set()
    for override in body.recipient_overrides:
        if not override.include:
            excluded_ids.add(override.practitioner_id)

    final_recipients = [p for p in all_recipients if p.id not in excluded_ids]

    now = datetime.now(UTC)
    workflow_run_id = str(uuid.uuid4())
    workflow_run = WorkflowRun(
        id=workflow_run_id,
        workflow_name="nudge_campaign",
        status="running",
        started_at=now,
    )
    db.add(workflow_run)

    nudge_ids: list[str] = []
    for p in final_recipients:
        nudge = Nudge(
            id=str(uuid.uuid4()),
            practitioner_id=p.id,
            nudge_type="campaign",
            channel="in_app",
            content=body.message_body,
            subject=body.message_subject,
            status="sent",
            sent_at=now,
            is_read=False,
            nudge_category_id=body.category_id,
            created_by_admin_id=session.admin_user_id,
        )
        db.add(nudge)
        nudge_ids.append(nudge.id)

    workflow_run.status = "completed"
    workflow_run.completed_at = now
    await db.commit()

    return SendNudgesResponse(
        sent_count=len(nudge_ids),
        workflow_run_id=workflow_run_id,
        nudge_ids=nudge_ids,
    )


@router.get("/nudges/sent", response_model=list[SentCampaignSummary])
async def list_sent_campaigns(
    db: AsyncSession = Depends(get_db),
    _session: SessionInfo = Depends(require_admin_or_leadership),
    limit: int = Query(20, le=100),
) -> list[SentCampaignSummary]:
    """List sent campaign summaries. Admin or leadership."""
    result = await db.execute(
        select(
            Nudge.nudge_category_id,
            Nudge.subject,
            Nudge.sent_at,
            func.count(Nudge.id).label("cnt"),
        )
        .where(Nudge.nudge_type == "campaign", Nudge.status == "sent")
        .group_by(Nudge.nudge_category_id, Nudge.subject, Nudge.sent_at)
        .order_by(Nudge.sent_at.desc())
        .limit(limit)
    )
    rows = result.all()

    # Fetch category titles
    cat_ids = {r.nudge_category_id for r in rows if r.nudge_category_id}
    cat_titles: dict[str, str | None] = {}
    if cat_ids:
        cat_result = await db.execute(select(NudgeCategory).where(NudgeCategory.id.in_(cat_ids)))
        for cat in cat_result.scalars():
            cat_titles[cat.id] = cat.title

    return [
        SentCampaignSummary(
            category_id=r.nudge_category_id,
            category_title=cat_titles.get(r.nudge_category_id) if r.nudge_category_id else None,
            sent_at=r.sent_at,
            recipient_count=r.cnt,
            subject=r.subject,
        )
        for r in rows
    ]


# ── Practitioner nudge inbox ────────────────────────────────────────────────────

@router.get("/practitioners/{practitioner_id}/nudges", response_model=list[NudgeReadExtended])
async def list_practitioner_nudges(
    practitioner_id: str,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> list[NudgeReadExtended]:
    """Return a practitioner's nudge inbox (unread first). Self-only."""
    enforce_self_or_admin(session, practitioner_id)
    p = await db.get(Practitioner, practitioner_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")

    result = await db.execute(
        select(Nudge)
        .where(Nudge.practitioner_id == practitioner_id, Nudge.status == "sent")
        .order_by(Nudge.is_read.asc(), Nudge.created_at.desc())
    )
    nudges = result.scalars().all()
    return [NudgeReadExtended.model_validate(n) for n in nudges]


@router.patch("/nudges/{nudge_id}/read", response_model=NudgeMarkReadResponse)
async def mark_nudge_read(
    nudge_id: str,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> NudgeMarkReadResponse:
    """Mark a nudge as read. Only the recipient may call this."""
    nudge = await db.get(Nudge, nudge_id)
    if nudge is None:
        raise HTTPException(status_code=404, detail="Nudge not found")
    # Self-only enforcement
    if session.identity_type == "practitioner" and nudge.practitioner_id != session.practitioner_id:
        raise HTTPException(status_code=403, detail="Not your nudge")
    nudge.is_read = True
    nudge.read_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(nudge)
    return NudgeMarkReadResponse.model_validate(nudge)


@router.get("/practitioners/{practitioner_id}/nudges/unread-count", response_model=UnreadCountResponse)
async def get_unread_nudge_count(
    practitioner_id: str,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> UnreadCountResponse:
    """Return count of unread sent nudges. Self-only, used for badge polling."""
    enforce_self_or_admin(session, practitioner_id)
    result = await db.execute(
        select(func.count()).select_from(Nudge).where(
            Nudge.practitioner_id == practitioner_id,
            Nudge.status == "sent",
            Nudge.is_read.is_(False),
        )
    )
    count = result.scalar() or 0
    return UnreadCountResponse(unread_count=count)


# ── Mastery history ─────────────────────────────────────────────────────────────

@router.get("/practitioners/{practitioner_id}/mastery-history", response_model=MasteryHistoryResponse)
async def get_mastery_history(
    practitioner_id: str,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
    skill_id: str | None = Query(None),
    days: int = Query(30, ge=1, le=90),
) -> MasteryHistoryResponse:
    """Return mastery history time-series. Self-only."""
    enforce_self_or_admin(session, practitioner_id)
    p = await db.get(Practitioner, practitioner_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")

    cutoff = datetime.now(UTC) - timedelta(days=days)
    query = (
        select(MasteryHistory, Skill.name.label("skill_name"))
        .join(Skill, MasteryHistory.skill_id == Skill.id)
        .where(
            MasteryHistory.practitioner_id == practitioner_id,
            MasteryHistory.recorded_at >= cutoff,
        )
        .order_by(MasteryHistory.recorded_at.asc())
    )
    if skill_id:
        query = query.where(MasteryHistory.skill_id == skill_id)

    result = await db.execute(query)
    rows = result.all()

    points = [
        MasteryHistoryPoint(
            skill_id=row.MasteryHistory.skill_id,
            skill_name=row.skill_name,
            mastery_score=float(row.MasteryHistory.mastery_score),
            recorded_at=row.MasteryHistory.recorded_at,
        )
        for row in rows
    ]
    return MasteryHistoryResponse(points=points, practitioner_id=practitioner_id)


# ── Adoption trends (real-time, no nightly batch) ─────────────────────────────

@router.get("/practitioners/{practitioner_id}/adoption-trends", response_model=AdoptionTrendsResponse)
async def get_adoption_trends(
    practitioner_id: str,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
    days: int = Query(90, ge=14, le=365),
) -> AdoptionTrendsResponse:
    """Real-time adoption trend: self-assessed score vs. weekly quiz performance.

    Trained score  = skill_profile_snapshots.mastery_score (Skill Profiler output
                     from self-assessment signals — no external usage data needed).
    Adoption score = weekly average of attempt.score for that skill's items.
    Gap            = trained − quiz_avg  (positive = underperforming vs. self-assessment;
                     negative = exceeding self-assessment).

    No nightly batch required — computed fresh on every request.
    """
    from collections import defaultdict

    enforce_self_or_admin(session, practitioner_id)
    p = await db.get(Practitioner, practitioner_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")

    now = datetime.now(UTC)
    computed_at = now.isoformat()

    # 1. Self-assessed score per skill (Skill Profiler synthesis of self-assessment)
    snap_result = await db.execute(
        select(SkillProfileSnapshot, Skill.name.label("skill_name"))
        .join(Skill, SkillProfileSnapshot.skill_id == Skill.id)
        .where(SkillProfileSnapshot.practitioner_id == practitioner_id)
        .order_by(Skill.name)
    )
    snap_rows = snap_result.all()

    if not snap_rows:
        return AdoptionTrendsResponse(
            practitioner_id=practitioner_id,
            skills=[],
            computed_at=computed_at,
        )

    # 2. Quiz attempts for this practitioner over the lookback window
    cutoff = now - timedelta(days=days)
    attempts_result = await db.execute(
        select(
            Attempt.attempted_at,
            Attempt.score,
            Item.skill_id,
        )
        .join(Item, Attempt.item_id == Item.id)
        .where(
            Attempt.practitioner_id == practitioner_id,
            Attempt.attempted_at >= cutoff,
        )
        .order_by(Attempt.attempted_at.asc())
    )
    attempt_rows = attempts_result.all()

    # 3. Bucket attempts by (skill_id, ISO-week Monday date)
    #    week_key -> list[score], also track the Monday datetime for labelling
    weekly_scores: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    weekly_monday: dict[str, dict[str, datetime]] = defaultdict(dict)

    for row in attempt_rows:
        dt = row.attempted_at
        monday = dt - timedelta(days=dt.weekday())  # Mon=0
        week_key = monday.date().isoformat()         # "2026-07-06"
        weekly_scores[row.skill_id][week_key].append(float(row.score))
        if week_key not in weekly_monday[row.skill_id]:
            weekly_monday[row.skill_id][week_key] = monday

    # 4. Build per-skill adoption trend
    skills: list[SkillAdoptionTrend] = []
    for snap_row, skill_name in snap_rows:
        skill_id = snap_row.skill_id
        self_assessed = float(snap_row.mastery_score)

        # Build sorted weekly quiz performance list
        quiz_performance: list[SkillQuizPeriod] = []
        for week_key in sorted(weekly_scores.get(skill_id, {}).keys()):
            scores = weekly_scores[skill_id][week_key]
            monday_dt = weekly_monday[skill_id][week_key]
            quiz_performance.append(SkillQuizPeriod(
                week_start=week_key,
                period_label=f"{monday_dt.strftime('%b')} {monday_dt.day}",
                avg_score=round(sum(scores) / len(scores), 3),
                attempt_count=len(scores),
            ))

        has_quiz_data = len(quiz_performance) > 0
        latest_quiz = quiz_performance[-1].avg_score if has_quiz_data else None
        current_gap = round(self_assessed - latest_quiz, 3) if latest_quiz is not None else 0.0

        # Direction: compare current gap to gap from the previous week
        if len(quiz_performance) >= 2:
            prev_gap = self_assessed - quiz_performance[-2].avg_score
            delta = current_gap - prev_gap          # positive = gap grew
            if delta < -0.03:
                gap_direction = "closing"
            elif delta > 0.03:
                gap_direction = "widening"
            else:
                gap_direction = "stable"
        elif has_quiz_data:
            gap_direction = "stable"
        else:
            gap_direction = "no_data"

        skills.append(SkillAdoptionTrend(
            skill_id=skill_id,
            skill_name=skill_name,
            self_assessed_score=self_assessed,
            quiz_performance=quiz_performance,
            current_gap=current_gap,
            gap_direction=gap_direction,
            has_quiz_data=has_quiz_data,
        ))

    # Sort: skills with quiz data first (largest absolute gap first), then unstarted skills
    skills.sort(key=lambda s: (not s.has_quiz_data, -abs(s.current_gap) if s.has_quiz_data else 0))

    return AdoptionTrendsResponse(
        practitioner_id=practitioner_id,
        skills=skills,
        computed_at=computed_at,
    )
