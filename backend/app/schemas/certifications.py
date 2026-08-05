"""Pydantic schemas for the certification catalog and advisor."""

from datetime import date, datetime

from pydantic import BaseModel, Field


# ── Catalog reads ─────────────────────────────────────────────────────────────

class CertificationProviderRead(BaseModel):
    id: str
    name: str
    website: str | None

    model_config = {"from_attributes": True}


class CertificationSkillRead(BaseModel):
    skill_id: str
    weight: float

    model_config = {"from_attributes": True}


class CertificationRead(BaseModel):
    id: str
    code: str
    name: str
    level: str
    requires_coding_background: bool
    typical_audience: str | None
    focus_area: str | None
    exam_format: str | None
    eligibility_notes: str | None
    external_url: str | None
    is_active: bool
    last_verified_at: date | None
    provider: CertificationProviderRead
    certification_skills: list[CertificationSkillRead] = []

    model_config = {"from_attributes": True}


# ── Certification Advisor I/O ─────────────────────────────────────────────────

class CertificationContext(BaseModel):
    """One catalog row passed to the advisor as structured context (not baked into prompt)."""

    code: str
    name: str
    provider_name: str
    level: str
    requires_coding_background: bool
    typical_audience: str | None
    focus_area: str | None
    eligibility_notes: str | None


class QuestionnaireAnswers(BaseModel):
    """The four questionnaire answers — matches the architecture.md design."""

    # Q1: which provider are they most interested in?
    provider_preference: str | None = Field(
        None,
        description="anthropic | aws | google | microsoft | null (no preference)",
    )
    # Q2: do they write code?
    writes_code: bool
    # Q3: day-to-day focus
    focus_area: str = Field(
        ...,
        description="advising | building | architecting",
    )
    # Q4: experience level
    experience_level: str = Field(
        ...,
        description="new | some | experienced",
    )


class AdvisorRequest(BaseModel):
    """What the API route receives — answers + which practitioner is asking."""

    practitioner_id: str
    answers: QuestionnaireAnswers


class AdvisorOutput(BaseModel):
    """Structured output the Certification Advisor agent returns."""

    primary_recommendation_code: str = Field(
        ...,
        description="Certification code (e.g. CCAO-F) for the primary recommendation.",
    )
    primary_rationale: str = Field(
        ...,
        description="One-paragraph rationale for the primary pick.",
    )
    alternative_code: str | None = Field(
        None,
        description="Code for an alternative, when a genuine trade-off exists.",
    )
    alternative_rationale: str | None = Field(
        None,
        description="Short rationale naming the trade-off vs. the primary pick.",
    )


class AdvisorResponse(BaseModel):
    """What the API route returns to the caller."""

    practitioner_id: str
    advisor_response_id: str
    goal_id: str
    recommendation: AdvisorOutput


# ── Certification goal ────────────────────────────────────────────────────────

class CertificationGoalRead(BaseModel):
    id: str
    practitioner_id: str
    certification_id: str
    certification_code: str
    status: str
    recommended_at: datetime
    selected_at: datetime | None
    achieved_at: datetime | None

    model_config = {"from_attributes": True}


class CertificationGoalUpdate(BaseModel):
    """Move a goal's status — e.g. recommended → selected."""

    status: str = Field(..., description="selected | in_progress | achieved | abandoned")
