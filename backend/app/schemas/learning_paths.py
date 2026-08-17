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
    # Phase 17.5: background quiz generation state — pending | ready | failed
    quiz_status: str = "pending"

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
    # Phase 17.7: True = background task was launched (generation in progress, not complete)
    quiz_generating: bool = False
    quiz_skipped_reason: str | None = None  # "unanswered_items" | None


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


class RoundMetricsPerSkill(BaseModel):
    """Round-based mastery metrics for one skill — passed to the Skill Profiler."""

    skill_id: str
    rounds_completed: int
    mastery_ceiling: float
    weighted_accuracy: float
    current_mastery_score: float


class SkillProfilerInput(BaseModel):
    """Input to the Skill Profiler agent.

    Phase 9.4: only quiz_attempt events are passed. Self-assessment ratings,
    certification completions, and project-history signals are no longer
    included in the profiler input — the radar is driven exclusively by
    demonstrated quiz performance.

    Phase 10.3: quiz_round_metrics are also passed when available.  The Skill
    Profiler uses current_mastery_score from round metrics as the primary signal
    rather than computing from raw events.
    """

    practitioner_id: str
    # Serialised quiz_attempt events from skill_profile_events (source='quiz_attempt' only)
    events: list[dict]
    # Phase 10.3: pre-computed round metrics — when present, these take precedence
    quiz_round_metrics: list[RoundMetricsPerSkill] = []


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
