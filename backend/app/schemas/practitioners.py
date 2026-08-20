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
    is_active: bool = True
    created_at: datetime

    model_config = {"from_attributes": True}


class ActivitySkillRow(BaseModel):
    """Per-skill engagement summary for the admin Activity tab."""
    skill_id: str
    skill_name: str
    mastery_score: float
    gap_pct: int
    quiz_rounds: int
    correct_count: int
    wrong_count: int
    correct_pct: int
    total_lesson_seconds: int
    lesson_count: int
    last_lesson_read_at: datetime | None = None


class ActivityMockExamRow(BaseModel):
    """One mock exam session summary for the admin Activity tab."""
    session_id: str
    certification_code: str
    status: str
    score_pct: int | None = None
    questions_answered: int
    total_questions: int
    time_spent_seconds: int
    started_at: datetime
    completed_at: datetime | None = None
    abandoned_reason: str | None = None


class ActivitySummaryStats(BaseModel):
    total_quiz_rounds: int
    total_attempts: int
    overall_correct_pct: int
    total_lesson_seconds: int
    mock_exams_completed: int
    latest_mock_score_pct: int | None = None


class ActivitySummaryResponse(BaseModel):
    summary_stats: ActivitySummaryStats
    skill_activity: list[ActivitySkillRow]
    mock_exams: list[ActivityMockExamRow]


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
    # Phase 10.3: trend info
    previous_mastery_score: float | None = None
    mastery_delta: float | None = None
    trend: str = "new"
    # Phase 13.4: domain linkage — populated when the practitioner's active cert
    # has agent-discovered skills with domain references.
    certification_domain_id: str | None = None
    certification_domain_name: str | None = None
    domain_weight_pct: float | None = None

    model_config = {"from_attributes": True}
