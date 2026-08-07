"""Pydantic schemas for Phase 7 — Smart Nudge Campaign system."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── NudgeCategory Agent I/O ──────────────────────────────────────────────────

class SkillGapSummaryItem(BaseModel):
    skill_name: str
    avg_gap_score: float
    practitioner_count: int


class NudgeCategoryInput(BaseModel):
    """Aggregate-only input to the NudgeCategoryGenerator — no PII."""
    total_practitioners: int
    practitioners_no_quiz_7d: int
    practitioners_no_quiz_14d: int
    practitioners_no_profile: int
    practitioners_profile_unrated: int
    skill_gap_summary: list[SkillGapSummaryItem] = []
    practitioners_stalled: int
    practitioners_near_cert_ready: int
    nudges_sent_last_7d: int


class NudgeCategoryItem(BaseModel):
    title: str = Field(..., description="Short label, e.g. 'Idle for 7+ days'")
    description: str = Field(..., description="One sentence explaining who qualifies")
    criteria: dict[str, Any] = Field(..., description="Machine-readable filter params")
    estimated_reach: int
    tone_hint: str = Field(..., description="One-line tone guidance")


class NudgeCategoryOutput(BaseModel):
    categories: list[NudgeCategoryItem] = Field(..., max_length=10)


# ── Nudge Campaign Composer I/O ──────────────────────────────────────────────

class NudgeCampaignComposerInput(BaseModel):
    """Input for campaign-mode nudge composition."""
    category_description: str
    tone_hint: str
    recipient_count: int


class NudgeCampaignComposerOutput(BaseModel):
    subject: str
    body: str
    tone_check: str = Field(..., description="One-sentence self-assessment of tone")


# ── API request/response schemas ─────────────────────────────────────────────

class NudgeCategoryRead(BaseModel):
    id: str
    title: str | None
    description: str
    criteria: dict[str, Any]
    is_custom: bool
    tone_hint: str | None
    estimated_reach: int | None
    created_by_admin_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RecipientPreview(BaseModel):
    id: str
    name: str
    email: str
    action_profile_summary: str  # e.g. "CCAF · AWS path"


class PreviewRecipientsResponse(BaseModel):
    recipients: list[RecipientPreview]
    total: int


class ComposePreviewResponse(BaseModel):
    subject: str
    body: str
    tone_check: str
    recipients: list[RecipientPreview]


class RecipientOverride(BaseModel):
    practitioner_id: str
    include: bool = True


class SendNudgesRequest(BaseModel):
    category_id: str
    message_subject: str
    message_body: str
    recipient_overrides: list[RecipientOverride] = []


class SendNudgesResponse(BaseModel):
    sent_count: int
    workflow_run_id: str
    nudge_ids: list[str]


class NudgeReadExtended(BaseModel):
    """Extended Nudge read schema with Phase 7 fields."""
    id: str
    practitioner_id: str
    nudge_type: str
    channel: str
    content: str
    subject: str | None
    status: str
    is_read: bool
    read_at: datetime | None
    nudge_category_id: str | None
    created_by_admin_id: str | None
    created_at: datetime
    sent_at: datetime | None
    composer_reasoning: str | None

    model_config = {"from_attributes": True}


class NudgeMarkReadResponse(BaseModel):
    id: str
    is_read: bool
    read_at: datetime | None

    model_config = {"from_attributes": True}


class UnreadCountResponse(BaseModel):
    unread_count: int


class MasteryHistoryPoint(BaseModel):
    skill_id: str
    skill_name: str
    mastery_score: float
    recorded_at: datetime

    model_config = {"from_attributes": True}


class MasteryHistoryResponse(BaseModel):
    points: list[MasteryHistoryPoint]
    practitioner_id: str


class SentCampaignSummary(BaseModel):
    """High-level campaign summary for the sent history panel."""
    category_id: str | None
    category_title: str | None
    sent_at: datetime
    recipient_count: int
    subject: str | None


# ── Adoption trend (Phase 7, revised) ─────────────────────────────────────────

class SkillQuizPeriod(BaseModel):
    """One week's quiz performance for a single skill."""
    week_start: str          # ISO date e.g. "2026-07-06"
    period_label: str        # Human label e.g. "Jul 6"
    avg_score: float         # 0.0–1.0 average of all attempt scores that week
    attempt_count: int


class SkillAdoptionTrend(BaseModel):
    """Per-skill comparison: self-assessed baseline vs. weekly quiz performance."""
    skill_id: str
    skill_name: str
    self_assessed_score: float    # from skill_profile_snapshots (Skill Profiler output)
    quiz_performance: list[SkillQuizPeriod]
    current_gap: float            # self_assessed − latest quiz avg; positive = underperforming
    gap_direction: str            # "closing" | "widening" | "stable" | "no_data"
    has_quiz_data: bool


class AdoptionTrendsResponse(BaseModel):
    practitioner_id: str
    skills: list[SkillAdoptionTrend]
    computed_at: str
