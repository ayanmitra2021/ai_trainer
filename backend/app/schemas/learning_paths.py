"""Pydantic schemas for learning paths and the generate_learning_path workflow."""

from datetime import datetime

from pydantic import BaseModel, Field


class LearningPathItemRead(BaseModel):
    id: str
    skill_id: str
    sequence_order: int
    resource_type: str
    status: str
    rationale: str | None

    model_config = {"from_attributes": True}


class LearningPathRead(BaseModel):
    id: str
    practitioner_id: str
    generated_at: datetime
    status: str
    workflow_run_id: str | None
    items: list[LearningPathItemRead] = []

    model_config = {"from_attributes": True}


class GenerateLearningPathRequest(BaseModel):
    """Trigger the generate_learning_path workflow for a practitioner."""

    practitioner_id: str


class GenerateLearningPathResponse(BaseModel):
    workflow_run_id: str
    learning_path_id: str
    status: str


# ── Agent I/O (used by agents, not directly by routes) ────────────────────────

class SkillScoreContext(BaseModel):
    """Compact skill snapshot for agent prompts."""

    skill_id: str
    skill_name: str
    mastery_score: float
    confidence: float


class CertGoalContext(BaseModel):
    """Certification goal context for the Curriculum Planner."""

    certification_code: str
    certification_name: str
    status: str
    # Skill weights from certification_skills
    skill_weights: dict[str, float]  # skill_id → weight


class SkillProfilerInput(BaseModel):
    """Input to the Skill Profiler agent.

    Phase 9.4: only quiz_attempt events are passed. Self-assessment ratings,
    certification completions, and project-history signals are no longer
    included in the profiler input — the radar is driven exclusively by
    demonstrated quiz performance.
    """

    practitioner_id: str
    # Serialised quiz_attempt events from skill_profile_events (source='quiz_attempt' only)
    events: list[dict]


class SkillScoreOutput(BaseModel):
    """One skill score — part of SkillProfilerOutput."""

    skill_id: str
    mastery_score: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str


class SkillProfilerOutput(BaseModel):
    """Structured output from the Skill Profiler agent."""

    skill_scores: list[SkillScoreOutput]
    summary: str


class PathItemSpec(BaseModel):
    """One item in the Curriculum Planner's output."""

    skill_id: str
    resource_type: str = Field(..., description="item_set | scenario_lab | external_reading")
    rationale: str


class CurriculumPlannerInput(BaseModel):
    """Input to the Curriculum Planner agent."""

    practitioner_id: str
    skill_scores: list[SkillScoreContext]
    certification_goal: CertGoalContext | None = None


class CurriculumPlannerOutput(BaseModel):
    """Structured output from the Curriculum Planner agent."""

    path_items: list[PathItemSpec]
    summary: str
