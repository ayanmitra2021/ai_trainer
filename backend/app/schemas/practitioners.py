"""Pydantic schemas for the practitioners API."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class PractitionerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., max_length=255)
    role: str | None = Field(None, max_length=255)
    practice: str | None = Field(None, max_length=255)
    seniority_level: str | None = Field(None, max_length=100)


class PractitionerRead(BaseModel):
    id: str
    name: str
    email: str
    role: str | None
    practice: str | None
    seniority_level: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PractitionerUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    role: str | None = Field(None, max_length=255)
    practice: str | None = Field(None, max_length=255)
    seniority_level: str | None = Field(None, max_length=100)


class SkillAssessmentItem(BaseModel):
    """One skill's self-assessed level — part of a SelfAssessmentRequest."""

    skill_id: str
    signal_strength: float = Field(..., ge=0.0, le=1.0)


class SelfAssessmentRequest(BaseModel):
    """Bulk self-assessment submission from a practitioner."""

    assessments: list[SkillAssessmentItem] = Field(..., min_length=1)


class SelfAssessmentResponse(BaseModel):
    events_written: int


class SkillSnapshotRead(BaseModel):
    skill_id: str
    skill_name: str
    mastery_score: float
    confidence: float
    last_computed_at: datetime
    # Phase 10.3: trend info — derived from mastery_history comparison
    previous_mastery_score: float | None = None
    mastery_delta: float | None = None
    trend: str = "new"  # improving | declining | stable | new

    model_config = {"from_attributes": True}
