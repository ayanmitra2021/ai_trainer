"""Pydantic schemas for items and attempts (Item-Writer / Grader agents)."""

from datetime import datetime

from pydantic import BaseModel, Field


# ── Items ─────────────────────────────────────────────────────────────────────

class ItemRead(BaseModel):
    id: str
    skill_id: str
    item_type: str
    prompt: str
    answer_key: dict
    trap_explanation: str | None
    difficulty: float
    calibration_stats: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Agent I/O: Item-Writer ────────────────────────────────────────────────────

class ItemWriterInput(BaseModel):
    """Input to the Item-Writer agent."""

    skill_id: str
    skill_name: str
    skill_description: str | None
    item_type: str = Field(..., description="mcq | free_text")
    target_difficulty: float = Field(0.5, ge=0.0, le=1.0)
    # Calibration hint: how many items already exist and their avg accuracy
    existing_items_count: int = 0
    low_accuracy_hint: bool = False  # True triggers difficulty recalibration prompt


class MCQAnswerKey(BaseModel):
    """Structured answer key for MCQ items."""

    options: list[str] = Field(..., min_length=3, max_length=5)
    correct_index: int
    trap_index: int | None = None


class FreeTextAnswerKey(BaseModel):
    """Structured answer key for free-text items."""

    model_answer: str
    key_points: list[str] = []


class ItemWriterOutput(BaseModel):
    """Structured output from the Item-Writer agent."""

    item_type: str
    prompt: str
    answer_key: dict  # MCQAnswerKey or FreeTextAnswerKey serialised
    trap_explanation: str | None = None
    difficulty: float = Field(..., ge=0.0, le=1.0)
    rationale: str  # Why this difficulty / why this trap


# ── Agent I/O: Grader ─────────────────────────────────────────────────────────

class GraderInput(BaseModel):
    """Input to the Grader agent."""

    item_id: str
    item_type: str  # mcq | free_text
    item_prompt: str
    answer_key: dict
    trap_explanation: str | None
    # Submitted response: {selected_index: int} for MCQ, {text: str} for free_text
    submitted_response: dict


class GraderOutput(BaseModel):
    """Structured output from the Grader agent."""

    score: float = Field(..., ge=0.0, le=1.0)
    grader_rationale: str
    # True if the practitioner picked the trap option; None for non-MCQ items
    is_trap_selected: bool | None = None


# ── Attempt I/O ───────────────────────────────────────────────────────────────

class AttemptCreate(BaseModel):
    """Submitted by the frontend when a practitioner answers an item."""

    practitioner_id: str
    item_id: str
    response: dict  # {selected_index: int} for MCQ, {text: str} for free_text


class AttemptRead(BaseModel):
    id: str
    practitioner_id: str
    item_id: str
    response: dict
    score: float
    grader_rationale: str
    is_trap_selected: bool | None
    attempted_at: datetime

    model_config = {"from_attributes": True}
