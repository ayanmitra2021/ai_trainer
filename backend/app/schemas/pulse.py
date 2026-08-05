"""Pydantic schemas for the Adoption Pulse (Phase 3) agents and API.

Covers: Usage-Signal, Correlation, Nudge Composer, Rollup Reporter agents,
plus the API read schemas for nudges, correlation snapshots, and rollups.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════════
# Usage-Signal Agent I/O  (Step 3.1)
# ═══════════════════════════════════════════════════════════════════════════════


class RawSignal(BaseModel):
    """One raw signal record as it arrives from the MCP server.

    The MCP server already attempts a skill mapping; skill_id may be null if
    the signal was ambiguous or unrecognised.
    """

    signal_type: str = Field(..., description="claude_code_session | git_commit | other")
    raw_ref: str = Field(..., description="Canonical pointer back to the source record")
    occurred_at: str = Field(..., description="ISO-8601 timestamp of the activity")
    # MCP-inferred mapping (conservative — null when ambiguous)
    skill_id: str | None = None
    skill_confidence: str | None = Field(
        None, description="'high' | 'low' | null — from the MCP server's mapping"
    )
    description: str | None = None  # free-text summary of what happened


class UsageSignalInput(BaseModel):
    """Input to the Usage-Signal Agent."""

    practitioner_id: str
    # Raw signals pre-fetched from mcp-usage-signals (may be empty)
    raw_signals: list[RawSignal] = []
    # Current skill graph — lets the agent cross-check or override MCP mappings
    known_skills: list[dict] = Field(
        default_factory=list,
        description="List of {skill_id, name, category} dicts for the active skill graph",
    )


class NormalizedEvent(BaseModel):
    """One usage event ready for persistence."""

    signal_type: str = Field(..., description="claude_code_session | git_commit | other")
    skill_id: str | None = Field(
        None,
        description="Mapped skill; null when ambiguous or unrecognised — do not guess",
    )
    raw_ref: str
    occurred_at: str
    mapping_reasoning: str | None = Field(
        None, description="Brief note on why this skill was chosen (or not)"
    )


class UsageSignalOutput(BaseModel):
    """Structured output from the Usage-Signal Agent."""

    normalized_events: list[NormalizedEvent]
    unmapped_count: int = Field(
        0, description="Number of events with null skill_id (ambiguous/unrecognised)"
    )
    summary: str


# ═══════════════════════════════════════════════════════════════════════════════
# Correlation Agent I/O  (Step 3.2)
# ═══════════════════════════════════════════════════════════════════════════════


class SkillSnapshotContext(BaseModel):
    """One skill's training record — passed to the Correlation Agent."""

    skill_id: str
    skill_name: str
    mastery_score: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    last_computed_at: str  # ISO-8601


class SkillUsageSummary(BaseModel):
    """Aggregated usage evidence for one skill — pre-computed by the workflow."""

    skill_id: str
    skill_name: str
    event_count_30d: int = Field(0, description="Usage events in the last 30 days")
    event_count_90d: int = Field(0, description="Usage events in the last 90 days")
    most_recent_at: str | None = None  # ISO-8601 of the most recent usage event


class CorrelationInput(BaseModel):
    """Input to the Correlation Agent.

    The workflow pre-computes usage summaries so the agent can focus on
    reasoning rather than raw event arithmetic.
    """

    practitioner_id: str
    skill_snapshots: list[SkillSnapshotContext]
    skill_usage_summaries: list[SkillUsageSummary]
    # Lookback window used when computing usage summaries (days)
    lookback_days: int = 30


class SkillCorrelationResult(BaseModel):
    """Correlation result for one practitioner × skill pair."""

    skill_id: str
    trained_score: float = Field(..., ge=0.0, le=1.0)
    # 0–1 adoption estimate: 0 = no recent usage evidence, 1 = consistent usage
    adoption_score: float = Field(..., ge=0.0, le=1.0)
    # Meaningful only when trained_score >= 0.5; capped at 1.0
    gap_score: float = Field(..., ge=0.0, le=1.0)
    # True when trained_score >= 0.5 AND adoption_score < 0.3
    has_adoption_gap: bool
    # 1–3 sentences — must name the evidence, not just state the conclusion
    reasoning: str


class CorrelationOutput(BaseModel):
    """Structured output from the Correlation Agent."""

    skill_correlations: list[SkillCorrelationResult]
    # Brief overall framing — must note correlation, not causation
    summary: str


# ═══════════════════════════════════════════════════════════════════════════════
# Nudge Composer Agent I/O  (Step 3.3)
# ═══════════════════════════════════════════════════════════════════════════════


class SkillGapContext(BaseModel):
    """One skill's gap context — passed to the Nudge Composer."""

    skill_name: str
    trained_score: float
    adoption_score: float
    gap_score: float


class NudgeComposerInput(BaseModel):
    """Input to the Nudge Composer Agent."""

    practitioner_id: str
    practitioner_name: str
    # Only skills with has_adoption_gap == True should be passed here
    skill_gaps: list[SkillGapContext]
    channel: str = Field("in_app", description="email | in_app")


class NudgeComposerOutput(BaseModel):
    """Structured output from the Nudge Composer Agent.

    should_compose == False means no nudge is needed (all gaps are trivial).
    When False, nudge_type and content must be None.
    """

    should_compose: bool
    nudge_type: str | None = Field(
        None, description="gap_alert | encouragement | reminder"
    )
    content: str | None = Field(
        None, description="The drafted nudge text ready for human review"
    )
    reasoning: str = Field(
        ..., description="Why a nudge was (or was not) composed"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Rollup Reporter Agent I/O  (Step 3.4)
# ═══════════════════════════════════════════════════════════════════════════════


class PractitionerCorrelationSummary(BaseModel):
    """Anonymized per-practitioner summary — no individual identifying data."""

    trained_skills_count: int
    skills_with_gap_count: int
    avg_trained_score: float
    avg_adoption_score: float
    avg_gap_score: float


class RollupReporterInput(BaseModel):
    """Input to the Rollup Reporter Agent.

    Practitioner summaries are anonymized before being passed here — the agent
    never receives a practitioner_id or name.
    """

    scope: str = Field(..., description="team | practice")
    scope_ref: str
    period_start: str  # ISO-8601
    period_end: str  # ISO-8601
    practitioner_count: int
    practitioner_summaries: list[PractitionerCorrelationSummary]
    min_cohort_size: int = Field(
        ...,
        description="Privacy threshold set in config — rollup is withheld if count < this",
    )


class RollupMetrics(BaseModel):
    """Aggregate metrics — only populated when min_cohort_size_met is True."""

    avg_gap_score: float
    pct_with_adoption_gap: float = Field(..., description="0–1 fraction")
    top_gap_skill_names: list[str] = Field(
        default_factory=list,
        description="Skill names most commonly showing adoption gaps (aggregated, not individual)",
    )
    adoption_trend: str = Field(
        ..., description="improving | stable | declining — relative to prior period if available"
    )


class RollupReporterOutput(BaseModel):
    """Structured output from the Rollup Reporter Agent."""

    min_cohort_size_met: bool
    # None when min_cohort_size_met is False — structural privacy gate
    metrics: RollupMetrics | None = None
    narrative: str | None = Field(
        None,
        description="Leadership-facing narrative summary; null when cohort too small",
    )
    reasoning: str


# ═══════════════════════════════════════════════════════════════════════════════
# API read schemas
# ═══════════════════════════════════════════════════════════════════════════════


class UsageEventRead(BaseModel):
    id: str
    practitioner_id: str
    signal_type: str
    skill_id: str | None
    raw_ref: str
    occurred_at: datetime
    ingested_at: datetime

    model_config = {"from_attributes": True}


class CorrelationSnapshotRead(BaseModel):
    id: str
    practitioner_id: str
    skill_id: str
    trained_score: float
    adoption_score: float
    gap_score: float
    has_adoption_gap: bool
    reasoning: str | None
    computed_at: datetime

    model_config = {"from_attributes": True}


class NudgeRead(BaseModel):
    id: str
    practitioner_id: str
    nudge_type: str
    channel: str
    content: str
    status: str
    created_at: datetime
    sent_at: datetime | None
    composer_reasoning: str | None

    model_config = {"from_attributes": True}


class NudgeApproveRequest(BaseModel):
    """Approve a drafted nudge for delivery."""
    pass  # no body needed — the action is implicit in the route


class RollupRead(BaseModel):
    id: str
    scope: str
    scope_ref: str
    period_start: datetime
    period_end: datetime
    metrics: dict | None
    narrative: str | None
    min_cohort_size_met: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════════════════
# Nightly Pulse workflow schemas
# ═══════════════════════════════════════════════════════════════════════════════


class NightlyPulseRequest(BaseModel):
    """Trigger the nightly_pulse workflow via the API."""

    practitioner_ids: list[str]
    scope: str = Field("practice", description="team | practice")
    scope_ref: str
    period_start: str  # ISO-8601 date
    period_end: str    # ISO-8601 date


class PractitionerPulseResult(BaseModel):
    practitioner_id: str
    status: str  # success | error
    error_message: str | None = None
    usage_events_written: int = 0
    correlation_snapshots_written: int = 0
    nudge_drafted: bool = False


class NightlyPulseResponse(BaseModel):
    workflow_run_id: str
    rollup_id: str | None
    practitioner_results: list[PractitionerPulseResult]
    status: str  # completed | partial | failed
