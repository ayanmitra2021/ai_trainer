"""Pydantic schemas for practitioner profiles — Phase 6.1 / Phase 10.1."""

from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class ProfileSkillRating(BaseModel):
    skill_id: str
    signal_strength: float = Field(..., ge=0.0, le=1.0)


class ProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    questionnaire_snapshot: dict | None = None
    # Phase 10.1: certification_id is required at the API layer (422 if absent
    # or null).  The DB column remains nullable to preserve existing data, but
    # every new profile created via this endpoint must reference a cert — the
    # certification is the anchor that drives domain scoring and item tagging.
    #
    # Enforcement uses @model_validator (not @field_validator) so the check
    # fires even when the caller omits the field entirely (in which case
    # Pydantic fills in the default None without invoking a field validator).
    certification_id: str | None = None

    @model_validator(mode="after")
    def certification_id_required(self) -> "ProfileCreate":
        if self.certification_id is None or not self.certification_id.strip():
            raise ValueError(
                "certification_id is required. "
                "A profile cannot be created without a certification — "
                "the certification determines which exam domains to load "
                "and what the domain gap chart measures."
            )
        return self


class ProfileUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=500)
    certification_id: str | None = None
    questionnaire_snapshot: dict | None = None


class ProfileSkillAssessmentRead(BaseModel):
    id: str
    profile_id: str
    skill_id: str
    signal_strength: float
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProfileRead(BaseModel):
    """Summary view — returned in list; mastery_pct is computed on the fly."""

    id: str
    practitioner_id: str
    name: str
    is_active: bool
    certification_id: str | None
    certification_code: str | None
    questionnaire_snapshot: dict | None
    created_at: datetime
    updated_at: datetime
    mastery_pct: float | None = None  # mean mastery of cert's skills; None if no cert
    # Step 9.2 forward-compat: always False until Step 9.3 adds the DB column.
    is_locked: bool = False
    # Phase 14.4: 'pending' | 'lm_scored' | 'degraded'
    domain_scoring_status: str = "pending"

    model_config = {"from_attributes": True}


class ProfileDetail(ProfileRead):
    """Full detail — includes the skill assessment rows."""

    skill_assessments: list[ProfileSkillAssessmentRead] = []


class SkillAssessmentUpsertRequest(BaseModel):
    assessments: list[ProfileSkillRating] = Field(..., min_length=0)


class SkillAssessmentUpsertResponse(BaseModel):
    rows_written: int
    # Phase 14.3: reflects whether the Domain Scorer ran via LLM or was degraded.
    domain_scoring_status: str = "pending"
