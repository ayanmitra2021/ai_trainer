"""Pydantic schemas for practitioner profiles — Phase 6.1."""

from datetime import datetime

from pydantic import BaseModel, Field


class ProfileSkillRating(BaseModel):
    skill_id: str
    signal_strength: float = Field(..., ge=0.0, le=1.0)


class ProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    questionnaire_snapshot: dict | None = None
    certification_id: str | None = None


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

    model_config = {"from_attributes": True}


class ProfileDetail(ProfileRead):
    """Full detail — includes the skill assessment rows."""

    skill_assessments: list[ProfileSkillAssessmentRead] = []


class SkillAssessmentUpsertRequest(BaseModel):
    assessments: list[ProfileSkillRating] = Field(..., min_length=0)


class SkillAssessmentUpsertResponse(BaseModel):
    rows_written: int
