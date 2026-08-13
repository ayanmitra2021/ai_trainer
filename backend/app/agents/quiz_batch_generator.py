"""Quiz Batch Generator Agent — Phase 12.2.

Generates exactly one starter MCQ per skill in the practitioner's active learning
path with a single LLM call.  Difficulty is calibrated to the skill's current
mastery_score so early learners get confidence-building questions while advanced
practitioners get near-exam-hard challenges.

The caller persists the returned items to the DB.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from app.agents.base import Agent
from app.schemas.items import MCQAnswerKey


# ── I/O models ────────────────────────────────────────────────────────────────


class SkillQuizSpec(BaseModel):
    """Descriptor for one skill in the batch request."""

    skill_id: str
    skill_name: str
    skill_description: str | None = None
    mastery_score: float = Field(0.0, ge=0.0, le=1.0)
    certification_domain_id: str | None = None
    certification_domain_name: str | None = None
    is_cert_evaluated: bool = False
    prior_generation_count: int = 0


class BatchQuizItem(BaseModel):
    """One generated quiz item in the batch response."""

    skill_id: str
    item_type: str = "mcq"
    prompt: str
    answer_key: MCQAnswerKey
    trap_explanation: str | None = None
    difficulty: float = Field(..., ge=0.0, le=1.0)
    certification_domain_id: str | None = None
    is_cert_evaluated: bool = False


class QuizBatchGeneratorInput(BaseModel):
    """Input to the QuizBatchGeneratorAgent."""

    skills: list[SkillQuizSpec]
    cert_code: str
    cert_name: str
    certification_domains: list[dict] | None = None  # [{id, name, description, weight_pct}]


class QuizBatchGeneratorOutput(BaseModel):
    """Structured output — exactly one item per input skill, in order."""

    items: list[BatchQuizItem]
    # Phase 13.5: cert/supp ratio audit — computed post-generation, not by LLM.
    # Default 0.0; the quiz-batch endpoint overrides these after calling the agent.
    cert_question_pct: float = 0.0
    supp_question_pct: float = 0.0


# ── Agent ─────────────────────────────────────────────────────────────────────


class QuizBatchGeneratorAgent(Agent[QuizBatchGeneratorInput, QuizBatchGeneratorOutput]):
    """Generates one calibrated MCQ per skill in a single LLM call.

    Output always has len(items) == len(input.skills) and items are in the
    same order as the input skills list.
    """

    name = "quiz_batch_generator"
    model = "claude-sonnet-5"
    output_model = QuizBatchGeneratorOutput
    max_tokens = 12000  # 16 skills × ~700 tokens + breathing room

    def _build_messages(self, input: QuizBatchGeneratorInput) -> list[dict[str, Any]]:
        skill_specs = []
        for i, s in enumerate(input.skills):
            # Map mastery to a target difficulty band for the prompt
            m = s.mastery_score
            if m <= 0.25:
                band = "0.30–0.45 (foundation — build confidence)"
            elif m <= 0.55:
                band = "0.45–0.65 (solidifying — apply concepts)"
            elif m <= 0.80:
                band = "0.65–0.80 (challenge — nuanced scenarios)"
            else:
                band = "0.80–0.95 (exam-hard — same bar as mock exam)"

            spec: dict[str, Any] = {
                "index": i,
                "skill_id": s.skill_id,
                "skill_name": s.skill_name,
                "skill_description": s.skill_description,
                "mastery_score": round(s.mastery_score, 3),
                "target_difficulty_band": band,
                "certification_domain_id": s.certification_domain_id,
                "certification_domain_name": s.certification_domain_name,
                "is_cert_evaluated": s.is_cert_evaluated,
            }
            if s.prior_generation_count > 0:
                spec["prior_generation_count"] = s.prior_generation_count
                spec["style_hint"] = (
                    "Vary the question style from previous rounds — "
                    "consider EXCEPT, MOST appropriate, FIRST step, or scenario-based formats."
                )
            skill_specs.append(spec)

        context = {
            "certification": {
                "code": input.cert_code,
                "name": input.cert_name,
            },
            "certification_domains": input.certification_domains,
            "skills": skill_specs,
        }

        return [
            {
                "role": "user",
                "content": (
                    f"## Quiz batch generation request\n\n"
                    f"```json\n{json.dumps(context, indent=2)}\n```\n\n"
                    f"Generate exactly one MCQ per skill entry above (in the same order).\n"
                    f"Return an `items` array with {len(input.skills)} elements."
                ),
            }
        ]
