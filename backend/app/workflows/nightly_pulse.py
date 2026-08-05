"""nightly_pulse workflow — Step 3.5.

Orchestrates: Usage-Signal → Correlation → Nudge Composer → Rollup Reporter.

One workflow_runs row is written at the start; its status is updated to
completed, partial (some practitioners failed), or failed (all failed or
rollup failed) at the end.

Each agent writes its own agent_runs row. A single practitioner's failure
does NOT abort the run — other practitioners still complete.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Message Batches API note (architecture.md §Model selection)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
For production, this workflow is a prime candidate for the Message Batches API
(50% discount, compatible with Structured Outputs). The current synchronous
implementation is intentional for v1 — it keeps the workflow testable with the
stub client and avoids batch-polling complexity before the system is proven.

Upgrade path when ready:
  1. Build a batch version of Agent.run() that submits via client.beta.messages.batches
  2. Poll until the batch completes (it's a nightly job — latency doesn't matter)
  3. Map batch results back to the per-practitioner flow below

Until that upgrade, the synchronous path is correct and costs about 2× more
per nightly run. At small practitioner counts (<100), this is negligible.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import ClaudeClient
from app.agents.correlation import CorrelationAgent
from app.agents.nudge_composer import NudgeComposerAgent
from app.agents.rollup_reporter import MINIMUM_COHORT_SIZE, RollupReporterAgent
from app.agents.usage_signal import UsageSignalAgent
from app.db.models import (
    CorrelationSnapshot,
    Nudge,
    Practitioner,
    Rollup,
    Skill,
    SkillProfileSnapshot,
    UsageEvent,
    WorkflowRun,
)
from app.schemas.pulse import (
    NightlyPulseResponse,
    NudgeComposerInput,
    PractitionerCorrelationSummary,
    PractitionerPulseResult,
    RawSignal,
    RollupReporterInput,
    SkillGapContext,
    SkillSnapshotContext,
    SkillUsageSummary,
    UsageSignalInput,
    CorrelationInput,
)


async def run_nightly_pulse(
    practitioner_ids: list[str],
    scope: str,
    scope_ref: str,
    period_start: datetime,
    period_end: datetime,
    db: AsyncSession,
    claude_client: ClaudeClient,
    *,
    # raw_signals_by_practitioner is the injection point for tests and for the
    # MCP-fetching layer. In production, callers should pre-fetch from
    # mcp-usage-signals and pass the data here. When None, the per-practitioner
    # step runs with empty signals (useful for testing correlation alone).
    raw_signals_by_practitioner: dict[str, list[dict[str, Any]]] | None = None,
) -> NightlyPulseResponse:
    """Run the full nightly_pulse workflow.

    Sequence:
      1. Write workflow_runs row (status=running)
      2. For each practitioner (failures isolated):
         a. Usage-Signal — normalize raw signals → write usage_events
         b. Correlation  — compare snapshots vs usage → write correlation_snapshots
         c. Nudge Composer — draft nudge if gap meaningful → write nudge (drafted)
      3. Rollup Reporter — aggregate all → write rollup
      4. Mark workflow_runs completed / partial / failed
    """
    workflow_run_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    workflow_run = WorkflowRun(
        id=workflow_run_id,
        workflow_name="nightly_pulse",
        triggered_by="scheduler",
        status="running",
        started_at=now,
    )
    db.add(workflow_run)
    await db.commit()

    # Fetch the skill graph once (shared across all practitioners)
    skills_result = await db.execute(select(Skill))
    all_skills = skills_result.scalars().all()
    known_skills = [
        {"skill_id": s.id, "name": s.name, "category": s.category}
        for s in all_skills
    ]

    practitioner_results: list[PractitionerPulseResult] = []
    all_correlation_snapshots: list[CorrelationSnapshot] = []

    for practitioner_id in practitioner_ids:
        result = await _run_practitioner_steps(
            practitioner_id=practitioner_id,
            workflow_run_id=workflow_run_id,
            db=db,
            claude_client=claude_client,
            known_skills=known_skills,
            period_end=period_end,
            raw_signals=(raw_signals_by_practitioner or {}).get(practitioner_id, []),
        )
        practitioner_results.append(result)

        # Collect correlation snapshots for the rollup step
        if result.status == "success":
            snaps = await db.execute(
                select(CorrelationSnapshot)
                .where(CorrelationSnapshot.practitioner_id == practitioner_id)
                .order_by(CorrelationSnapshot.computed_at.desc())
            )
            # Take the latest snapshot per skill for this run
            seen_skills: set[str] = set()
            for snap in snaps.scalars().all():
                if snap.skill_id not in seen_skills:
                    all_correlation_snapshots.append(snap)
                    seen_skills.add(snap.skill_id)

    # ── 3. Rollup Reporter ─────────────────────────────────────────────────
    rollup_id: str | None = None
    try:
        rollup_id = await _run_rollup(
            practitioner_ids=practitioner_ids,
            correlation_snapshots=all_correlation_snapshots,
            scope=scope,
            scope_ref=scope_ref,
            period_start=period_start,
            period_end=period_end,
            workflow_run_id=workflow_run_id,
            db=db,
            claude_client=claude_client,
        )
    except Exception as exc:
        # Rollup failure should not mark individual practitioner steps as failed
        # but does affect overall workflow status
        practitioner_results.append(
            PractitionerPulseResult(
                practitioner_id="__rollup__",
                status="error",
                error_message=str(exc),
            )
        )

    # ── 4. Finalise workflow status ────────────────────────────────────────
    success_count = sum(1 for r in practitioner_results if r.status == "success")
    error_count = sum(1 for r in practitioner_results if r.status == "error")

    if success_count == 0:
        overall_status = "failed"
    elif error_count > 0:
        overall_status = "partial"
    else:
        overall_status = "completed"

    workflow_run.status = overall_status
    workflow_run.completed_at = datetime.now(UTC)
    await db.commit()

    return NightlyPulseResponse(
        workflow_run_id=workflow_run_id,
        rollup_id=rollup_id,
        practitioner_results=[r for r in practitioner_results if r.practitioner_id != "__rollup__"],
        status=overall_status,
    )


async def _run_practitioner_steps(
    practitioner_id: str,
    workflow_run_id: str,
    db: AsyncSession,
    claude_client: ClaudeClient,
    known_skills: list[dict[str, Any]],
    period_end: datetime,
    raw_signals: list[dict[str, Any]],
) -> PractitionerPulseResult:
    """Run the per-practitioner steps. Returns a result even on failure."""
    result = PractitionerPulseResult(practitioner_id=practitioner_id, status="success")

    try:
        # ── 2a. Usage-Signal ───────────────────────────────────────────────
        raw_signal_objects = [
            RawSignal(
                signal_type=s.get("signal_type", "other"),
                raw_ref=s.get("raw_ref", f"unknown:{uuid.uuid4()}"),
                occurred_at=s.get("occurred_at", datetime.now(UTC).isoformat()),
                skill_id=s.get("skill_id"),
                skill_confidence=s.get("skill_confidence"),
                description=s.get("description"),
            )
            for s in raw_signals
        ]

        usage_input = UsageSignalInput(
            practitioner_id=practitioner_id,
            raw_signals=raw_signal_objects,
            known_skills=known_skills,
        )
        usage_agent = UsageSignalAgent(
            client=claude_client, db_session=db, workflow_run_id=workflow_run_id
        )
        usage_output = await usage_agent.run(usage_input)

        # Persist usage_events
        for event in usage_output.normalized_events:
            usage_event = UsageEvent(
                id=str(uuid.uuid4()),
                practitioner_id=practitioner_id,
                signal_type=event.signal_type,
                skill_id=event.skill_id,
                raw_ref=event.raw_ref,
                occurred_at=_parse_dt(event.occurred_at),
                ingested_at=datetime.now(UTC),
            )
            db.add(usage_event)
        await db.flush()
        result.usage_events_written = len(usage_output.normalized_events)

        # ── 2b. Correlation ────────────────────────────────────────────────
        # Fetch skill snapshots for this practitioner
        snaps_result = await db.execute(
            select(SkillProfileSnapshot, Skill)
            .join(Skill, Skill.id == SkillProfileSnapshot.skill_id)
            .where(SkillProfileSnapshot.practitioner_id == practitioner_id)
        )
        snapshots_with_skills = snaps_result.all()

        if not snapshots_with_skills:
            # No training data → skip correlation for this practitioner
            result.status = "success"
            return result

        skill_snapshots = [
            SkillSnapshotContext(
                skill_id=snap.skill_id,
                skill_name=skill.name,
                mastery_score=float(snap.mastery_score),
                confidence=float(snap.confidence),
                last_computed_at=snap.last_computed_at.isoformat(),
            )
            for snap, skill in snapshots_with_skills
        ]

        # Build usage summaries per skill (last 30 / 90 days)
        cutoff_30d = period_end - timedelta(days=30)
        cutoff_90d = period_end - timedelta(days=90)

        skill_usage_summaries: list[SkillUsageSummary] = []
        skill_name_map = {snap.skill_id: skill.name for snap, skill in snapshots_with_skills}

        for snap, skill in snapshots_with_skills:
            count_30_result = await db.execute(
                select(func.count(UsageEvent.id))
                .where(
                    UsageEvent.practitioner_id == practitioner_id,
                    UsageEvent.skill_id == snap.skill_id,
                    UsageEvent.occurred_at >= cutoff_30d,
                )
            )
            count_90_result = await db.execute(
                select(func.count(UsageEvent.id))
                .where(
                    UsageEvent.practitioner_id == practitioner_id,
                    UsageEvent.skill_id == snap.skill_id,
                    UsageEvent.occurred_at >= cutoff_90d,
                )
            )
            latest_result = await db.execute(
                select(UsageEvent.occurred_at)
                .where(
                    UsageEvent.practitioner_id == practitioner_id,
                    UsageEvent.skill_id == snap.skill_id,
                )
                .order_by(UsageEvent.occurred_at.desc())
                .limit(1)
            )
            count_30 = count_30_result.scalar_one()
            count_90 = count_90_result.scalar_one()
            latest = latest_result.scalar_one_or_none()

            skill_usage_summaries.append(
                SkillUsageSummary(
                    skill_id=snap.skill_id,
                    skill_name=skill.name,
                    event_count_30d=count_30,
                    event_count_90d=count_90,
                    most_recent_at=latest.isoformat() if latest else None,
                )
            )

        corr_input = CorrelationInput(
            practitioner_id=practitioner_id,
            skill_snapshots=skill_snapshots,
            skill_usage_summaries=skill_usage_summaries,
        )
        corr_agent = CorrelationAgent(
            client=claude_client, db_session=db, workflow_run_id=workflow_run_id
        )
        corr_output = await corr_agent.run(corr_input)

        # Persist correlation_snapshots
        for corr in corr_output.skill_correlations:
            snap = CorrelationSnapshot(
                id=str(uuid.uuid4()),
                practitioner_id=practitioner_id,
                skill_id=corr.skill_id,
                trained_score=corr.trained_score,
                adoption_score=corr.adoption_score,
                gap_score=corr.gap_score,
                has_adoption_gap=corr.has_adoption_gap,
                reasoning=corr.reasoning,
                computed_at=datetime.now(UTC),
            )
            db.add(snap)
        await db.flush()
        result.correlation_snapshots_written = len(corr_output.skill_correlations)

        # ── 2c. Nudge Composer ─────────────────────────────────────────────
        gap_skills = [
            c for c in corr_output.skill_correlations if c.has_adoption_gap
        ]

        if gap_skills:
            # Fetch practitioner name for the nudge
            practitioner = await db.get(Practitioner, practitioner_id)
            practitioner_name = practitioner.name if practitioner else "Practitioner"

            skill_gaps = [
                SkillGapContext(
                    skill_name=skill_name_map.get(c.skill_id, c.skill_id),
                    trained_score=c.trained_score,
                    adoption_score=c.adoption_score,
                    gap_score=c.gap_score,
                )
                for c in gap_skills
            ]

            nudge_input = NudgeComposerInput(
                practitioner_id=practitioner_id,
                practitioner_name=practitioner_name,
                skill_gaps=skill_gaps,
            )
            nudge_agent = NudgeComposerAgent(
                client=claude_client, db_session=db, workflow_run_id=workflow_run_id
            )
            nudge_output = await nudge_agent.run(nudge_input)

            if nudge_output.should_compose and nudge_output.content:
                nudge = Nudge(
                    id=str(uuid.uuid4()),
                    practitioner_id=practitioner_id,
                    nudge_type=nudge_output.nudge_type or "gap_alert",
                    channel="in_app",
                    content=nudge_output.content,
                    status="drafted",
                    created_at=datetime.now(UTC),
                    composer_reasoning=nudge_output.reasoning,
                )
                db.add(nudge)
                await db.flush()
                result.nudge_drafted = True

    except Exception as exc:
        result.status = "error"
        result.error_message = str(exc)

    return result


async def _run_rollup(
    practitioner_ids: list[str],
    correlation_snapshots: list[CorrelationSnapshot],
    scope: str,
    scope_ref: str,
    period_start: datetime,
    period_end: datetime,
    workflow_run_id: str,
    db: AsyncSession,
    claude_client: ClaudeClient,
) -> str:
    """Run the Rollup Reporter and persist a rollup row. Returns the rollup id."""
    practitioner_count = len(practitioner_ids)

    # Build anonymized summaries — no practitioner_id in these objects
    summaries_by_practitioner: dict[str, dict[str, Any]] = {}
    for snap in correlation_snapshots:
        pid = snap.practitioner_id
        if pid not in summaries_by_practitioner:
            summaries_by_practitioner[pid] = {
                "trained_scores": [],
                "adoption_scores": [],
                "gap_scores": [],
                "has_gap": False,
            }
        s = summaries_by_practitioner[pid]
        s["trained_scores"].append(float(snap.trained_score))
        s["adoption_scores"].append(float(snap.adoption_score))
        s["gap_scores"].append(float(snap.gap_score))
        if snap.has_adoption_gap:
            s["has_gap"] = True

    practitioner_summaries = []
    for pid, agg in summaries_by_practitioner.items():
        ts = agg["trained_scores"]
        as_ = agg["adoption_scores"]
        gs = agg["gap_scores"]
        practitioner_summaries.append(
            PractitionerCorrelationSummary(
                trained_skills_count=len(ts),
                skills_with_gap_count=sum(
                    1 for snap in correlation_snapshots
                    if snap.practitioner_id == pid and snap.has_adoption_gap
                ),
                avg_trained_score=sum(ts) / len(ts) if ts else 0.0,
                avg_adoption_score=sum(as_) / len(as_) if as_ else 0.0,
                avg_gap_score=sum(gs) / len(gs) if gs else 0.0,
            )
        )

    rollup_input = RollupReporterInput(
        scope=scope,
        scope_ref=scope_ref,
        period_start=period_start.isoformat(),
        period_end=period_end.isoformat(),
        practitioner_count=practitioner_count,
        practitioner_summaries=practitioner_summaries,
        min_cohort_size=MINIMUM_COHORT_SIZE,
    )

    rollup_agent = RollupReporterAgent(
        client=claude_client, db_session=db, workflow_run_id=workflow_run_id
    )
    rollup_output = await rollup_agent.run(rollup_input)

    rollup_id = str(uuid.uuid4())
    rollup = Rollup(
        id=rollup_id,
        scope=scope,
        scope_ref=scope_ref,
        period_start=period_start,
        period_end=period_end,
        metrics=rollup_output.metrics.model_dump() if rollup_output.metrics else None,
        narrative=rollup_output.narrative,
        min_cohort_size_met=rollup_output.min_cohort_size_met,
        created_at=datetime.now(UTC),
    )
    db.add(rollup)
    await db.commit()

    return rollup_id


def _parse_dt(s: str) -> datetime:
    """Parse an ISO-8601 string into a timezone-aware datetime (UTC assumed if naive)."""
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except ValueError:
        return datetime.now(UTC)
