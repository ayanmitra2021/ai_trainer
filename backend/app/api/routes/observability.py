"""Observability API — Step 5.1.

Internal admin-only view over agent_runs.

Routes:
  GET /observability/agent-runs   cost, latency, error rate summary + recent errors
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.session import SessionInfo, require_admin
from app.db.models import AgentRun
from app.db.session import get_db

router = APIRouter(prefix="/observability", tags=["observability"])


# ── Pydantic schemas ───────────────────────────────────────────────────────────

class AgentStats(BaseModel):
    agent_name: str
    run_count: int
    error_count: int
    error_rate: float
    avg_latency_ms: float | None
    avg_tokens_input: float | None
    avg_tokens_output: float | None


class RecentError(BaseModel):
    id: str
    agent_name: str
    error_message: str | None
    workflow_run_id: str | None
    started_at: datetime


class ObservabilityReport(BaseModel):
    period_hours: int
    total_runs: int
    error_count: int
    error_rate: float
    avg_latency_ms: float | None
    by_agent: list[AgentStats]
    recent_errors: list[RecentError]


# ── Route ─────────────────────────────────────────────────────────────────────

@router.get("/agent-runs", response_model=ObservabilityReport)
async def agent_run_summary(
    db: AsyncSession = Depends(get_db),
    _session: SessionInfo = Depends(require_admin),
    hours: int = Query(
        default=24,
        ge=1,
        le=720,
        description="Look-back window in hours (1–720). Default 24.",
    ),
) -> ObservabilityReport:
    """Return cost, latency, and error-rate summary for the last N hours.

    This is the primary observability view for admins to catch regressions,
    track token spend, and identify agents with elevated error rates.

    Scenario: A recent agent error is surfaced in the observability view,
    including the error message.
    """
    since = datetime.now(UTC) - timedelta(hours=hours)

    # All runs in the window
    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.started_at >= since)
        .order_by(AgentRun.started_at.desc())
    )
    runs: list[AgentRun] = list(result.scalars().all())

    total = len(runs)
    errors = [r for r in runs if r.status == "error"]
    error_count = len(errors)

    latencies = [r.latency_ms for r in runs if r.latency_ms is not None]
    avg_latency = sum(latencies) / len(latencies) if latencies else None

    # Per-agent breakdown
    by_name: dict[str, list[AgentRun]] = {}
    for r in runs:
        by_name.setdefault(r.agent_name, []).append(r)

    by_agent: list[AgentStats] = []
    for name, agent_runs in sorted(by_name.items()):
        agent_errors = [r for r in agent_runs if r.status == "error"]
        a_latencies = [r.latency_ms for r in agent_runs if r.latency_ms is not None]
        ti_vals = [r.tokens_input for r in agent_runs if r.tokens_input is not None]
        to_vals = [r.tokens_output for r in agent_runs if r.tokens_output is not None]
        by_agent.append(
            AgentStats(
                agent_name=name,
                run_count=len(agent_runs),
                error_count=len(agent_errors),
                error_rate=len(agent_errors) / len(agent_runs) if agent_runs else 0.0,
                avg_latency_ms=sum(a_latencies) / len(a_latencies) if a_latencies else None,
                avg_tokens_input=sum(ti_vals) / len(ti_vals) if ti_vals else None,
                avg_tokens_output=sum(to_vals) / len(to_vals) if to_vals else None,
            )
        )

    # Recent errors (most recent 20)
    recent_errors: list[RecentError] = [
        RecentError(
            id=r.id,
            agent_name=r.agent_name,
            error_message=r.error_message,
            workflow_run_id=r.workflow_run_id,
            started_at=r.started_at,
        )
        for r in errors[:20]
    ]

    return ObservabilityReport(
        period_hours=hours,
        total_runs=total,
        error_count=error_count,
        error_rate=error_count / total if total else 0.0,
        avg_latency_ms=avg_latency,
        by_agent=by_agent,
        recent_errors=recent_errors,
    )
