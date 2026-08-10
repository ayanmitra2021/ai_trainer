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
    """Questionnaire answers — original four required fields + optional Phase 6.2 fields."""

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

    # ── Phase 6.2 optional enrichment fields ──────────────────────────────
    ai_experience_years: str | None = Field(
        None,
        description="none | under_1 | 1_to_3 | over_3",
    )
    primary_job_role: str | None = Field(
        None,
        description="developer | architect | consultant | manager | researcher | other",
    )
    deploys_llms_in_production: bool | None = Field(
        None,
        description="Whether they currently deploy LLMs in production",
    )
    prompt_engineering_familiarity: str | None = Field(
        None,
        description="none | basic | intermediate | advanced",
    )
    mentors_others_on_ai: bool | None = Field(
        None,
        description="Whether they manage or mentor others on AI topics",
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

    # ── Cert metadata — always populated so auto-create works ────────────────
    # These fields allow the route to create a new Certification row when the
    # recommended code is not already in the catalog (e.g. when a non-Anthropic
    # LLM recommends a cert we haven't seeded yet).
    cert_full_name: str | None = Field(
        None,
        description=(
            "Full display name of the recommended certification "
            "(e.g. 'Claude Certified Associate – Foundations')."
        ),
    )
    cert_provider_name: str | None = Field(
        None,
        description=(
            "Provider name exactly as shown in the catalog "
            "(e.g. 'Anthropic', 'AWS', 'Google Cloud', 'Microsoft')."
        ),
    )
    cert_level: str | None = Field(
        None,
        description="Level: foundational | associate | professional.",
    )
    cert_requires_coding: bool | None = Field(
        None,
        description="True if a coding background is required, false otherwise.",
    )


class AdvisorResponse(BaseModel):
    """What the API route returns to the caller."""

    practitioner_id: str
    advisor_response_id: str
    goal_id: str
    recommendation: AdvisorOutput
    is_new_certification: bool = Field(
        False,
        description=(
            "True when the recommended certification was not previously in the "
            "catalog and has been auto-created from the LLM's metadata. "
            "The frontend uses this to show an informational notice."
        ),
    )


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
