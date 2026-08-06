"""Adoption Pulse API routes — Step 3.6.

Routes:
  POST /pulse/run                                trigger nightly_pulse workflow
  GET  /practitioners/{id}/correlation-snapshots list correlation history
  GET  /nudges                                   list nudges (filterable by status)
  POST /nudges/{id}/approve                      approve a drafted nudge
  GET  /rollups                                  list rollups
  GET  /rollups/{id}                             fetch a single rollup

Step 5.2 — Auth applied:
  - POST /pulse/run                         → require_admin
  - GET  /practitioners/{id}/corr-snapshots → require_any_authenticated + self-enforcement
  - GET  /nudges                            → require_admin_or_leadership
  - POST /nudges/{id}/approve               → require_admin
  - GET  /rollups                           → require_admin_or_leadership
  - GET  /rollups/{id}                      → require_admin_or_leadership
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.session import (
    SessionInfo,
    enforce_self_or_admin,
    require_admin,
    require_admin_or_leadership,
    require_any_authenticated,
)
from app.config import settings
from app.db.models import CorrelationSnapshot, Nudge, Practitioner, Rollup
from app.db.session import get_db
from app.schemas.pulse import (
    CorrelationSnapshotRead,
    NightlyPulseRequest,
    NightlyPulseResponse,
    NudgeRead,
    RollupRead,
)

router = APIRouter(tags=["pulse"])


# ── Nightly Pulse trigger ──────────────────────────────────────────────────────

@router.post("/pulse/run", response_model=NightlyPulseResponse, status_code=202)
async def trigger_nightly_pulse(
    body: NightlyPulseRequest,
    db: AsyncSession = Depends(get_db),
    _session: SessionInfo = Depends(require_admin),
) -> NightlyPulseResponse:
    """Trigger the nightly_pulse workflow. Admin only."""
    for pid in body.practitioner_ids:
        p = await db.get(Practitioner, pid)
        if p is None:
            raise HTTPException(
                status_code=404, detail=f"Practitioner {pid!r} not found"
            )

    import anthropic as anthropic_lib

    from app.workflows.nightly_pulse import run_nightly_pulse

    claude_client = anthropic_lib.AsyncAnthropic(api_key=settings.anthropic_api_key)
    period_start = datetime.fromisoformat(body.period_start).replace(tzinfo=UTC)
    period_end = datetime.fromisoformat(body.period_end).replace(tzinfo=UTC)

    result = await run_nightly_pulse(
        practitioner_ids=body.practitioner_ids,
        scope=body.scope,
        scope_ref=body.scope_ref,
        period_start=period_start,
        period_end=period_end,
        db=db,
        claude_client=claude_client,
    )
    return result


# ── Correlation snapshots ──────────────────────────────────────────────────────

@router.get(
    "/practitioners/{practitioner_id}/correlation-snapshots",
    response_model=list[CorrelationSnapshotRead],
)
async def list_correlation_snapshots(
    practitioner_id: str,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
    skill_id: str | None = Query(None, description="Filter by skill"),
    gaps_only: bool = Query(False, description="Return only rows with has_adoption_gap=True"),
) -> list[CorrelationSnapshotRead]:
    """Return correlation history for a practitioner, newest first."""
    enforce_self_or_admin(session, practitioner_id)
    practitioner = await db.get(Practitioner, practitioner_id)
    if practitioner is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")

    query = (
        select(CorrelationSnapshot)
        .where(CorrelationSnapshot.practitioner_id == practitioner_id)
        .order_by(CorrelationSnapshot.computed_at.desc())
    )
    if skill_id:
        query = query.where(CorrelationSnapshot.skill_id == skill_id)
    if gaps_only:
        query = query.where(CorrelationSnapshot.has_adoption_gap.is_(True))

    result = await db.execute(query)
    snapshots = result.scalars().all()
    return [CorrelationSnapshotRead.model_validate(s) for s in snapshots]


# ── Nudges ─────────────────────────────────────────────────────────────────────

@router.get("/nudges", response_model=list[NudgeRead])
async def list_nudges(
    db: AsyncSession = Depends(get_db),
    _session: SessionInfo = Depends(require_admin_or_leadership),
    practitioner_id: str | None = Query(None),
    status: str | None = Query(None, description="drafted | approved | sent"),
) -> list[NudgeRead]:
    """List nudges. Admin or leadership only."""
    query = select(Nudge).order_by(Nudge.created_at.desc())
    if practitioner_id:
        query = query.where(Nudge.practitioner_id == practitioner_id)
    if status:
        query = query.where(Nudge.status == status)

    result = await db.execute(query)
    nudges = result.scalars().all()
    return [NudgeRead.model_validate(n) for n in nudges]


@router.post("/nudges/{nudge_id}/approve", response_model=NudgeRead)
async def approve_nudge(
    nudge_id: str,
    db: AsyncSession = Depends(get_db),
    _session: SessionInfo = Depends(require_admin),
) -> NudgeRead:
    """Approve a drafted nudge. Admin only."""
    nudge = await db.get(Nudge, nudge_id)
    if nudge is None:
        raise HTTPException(status_code=404, detail="Nudge not found")
    if nudge.status != "drafted":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot approve a nudge with status '{nudge.status}' — only 'drafted' nudges can be approved",
        )

    nudge.status = "approved"
    await db.commit()
    await db.refresh(nudge)
    return NudgeRead.model_validate(nudge)


# ── Rollups ────────────────────────────────────────────────────────────────────

@router.get("/rollups", response_model=list[RollupRead])
async def list_rollups(
    db: AsyncSession = Depends(get_db),
    _session: SessionInfo = Depends(require_admin_or_leadership),
    scope: str | None = Query(None, description="team | practice"),
    scope_ref: str | None = Query(None),
) -> list[RollupRead]:
    """List rollups. Admin or leadership only."""
    query = select(Rollup).order_by(Rollup.created_at.desc())
    if scope:
        query = query.where(Rollup.scope == scope)
    if scope_ref:
        query = query.where(Rollup.scope_ref == scope_ref)

    result = await db.execute(query)
    rollups = result.scalars().all()
    return [RollupRead.model_validate(r) for r in rollups]


@router.get("/rollups/{rollup_id}", response_model=RollupRead)
async def get_rollup(
    rollup_id: str,
    db: AsyncSession = Depends(get_db),
    _session: SessionInfo = Depends(require_admin_or_leadership),
) -> RollupRead:
    """Fetch a single rollup. Admin or leadership only.

    When min_cohort_size_met is False, metrics and narrative are null.
    """
    rollup = await db.get(Rollup, rollup_id)
    if rollup is None:
        raise HTTPException(status_code=404, detail="Rollup not found")
    return RollupRead.model_validate(rollup)
