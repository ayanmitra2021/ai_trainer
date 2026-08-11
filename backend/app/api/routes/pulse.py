"""Adoption Pulse API routes — Step 3.6 (updated Phase 9.1).

Phase 9.1 changes:
  - Removed POST /pulse/run  (nightly_pulse workflow trigger)
  - Removed GET  /rollups    (list rollups)
  - Removed GET  /rollups/{id} (single rollup)

The Rollup Reporter agent and the nightly_pulse workflow have been removed from
the active product. The correlation agent and nudge routes below are unaffected.

Remaining routes:
  GET  /practitioners/{id}/correlation-snapshots list correlation history
  GET  /nudges                                   list nudges (filterable by status)
  POST /nudges/{id}/approve                      approve a drafted nudge

Step 5.2 — Auth applied:
  - GET  /practitioners/{id}/corr-snapshots → require_any_authenticated + self-enforcement
  - GET  /nudges                            → require_admin_or_leadership
  - POST /nudges/{id}/approve               → require_admin
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
from app.db.models import CorrelationSnapshot, Nudge, Practitioner
from app.db.session import get_db
from app.schemas.pulse import (
    CorrelationSnapshotRead,
    NudgeRead,
)

router = APIRouter(tags=["pulse"])


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
    """Approve a drafted nudge and mark as sent. Admin only.

    Nightly-pulse nudges are created with status 'drafted' and require approval
    before delivery. Approving moves them directly to 'sent' with a timestamp
    since there's no separate delivery mechanism for individual nudges.
    """
    nudge = await db.get(Nudge, nudge_id)
    if nudge is None:
        raise HTTPException(status_code=404, detail="Nudge not found")
    if nudge.status != "drafted":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot approve a nudge with status '{nudge.status}' — only 'drafted' nudges can be approved",
        )

    now = datetime.now(UTC)
    nudge.status = "sent"
    nudge.sent_at = now
    await db.commit()
    await db.refresh(nudge)
    return NudgeRead.model_validate(nudge)
