"""Byte-Sized Lesson Agent — Phase 18.2.

Generates a short (≤5 min read), engaging, bulleted write-up per skill gap
with curated external links. Called once per skill in a background task after
path generation (same lifecycle as QuizBatchGeneratorAgent).
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from app.agents.base import Agent


# ── I/O models ────────────────────────────────────────────────────────────────


class ExternalLink(BaseModel):
    """A curated external resource."""
    title: str
    url: str
    type: str  # 'blog' | 'docs' | 'video'


class ByteSizedLessonInput(BaseModel):
    """Input to the ByteSizedLessonAgent."""
    skill_name: str
    skill_description: str
    current_mastery_score: float = Field(..., ge=0.0, le=1.0)
    target_mastery_score: float = Field(0.85, ge=0.0, le=1.0)
    certification_name: str
    domain_name: str
    domain_description: str


class ByteSizedLessonOutput(BaseModel):
    """Output from the ByteSizedLessonAgent."""
    what_missing: str = Field(..., description="1-2 sentence plain-English gap summary for table column (no Markdown)")
    content_md: str = Field(..., description="Full Markdown write-up ≤750 words with hook, key concepts, pitfalls, quick check, sign-off")
    external_links: list[ExternalLink] = Field(..., min_length=3, max_length=5)
    estimated_read_minutes: int = Field(..., ge=1, le=5)


class ByteSizedLessonAgent(Agent[ByteSizedLessonInput, ByteSizedLessonOutput]):
    """Generates a crisp, engaging micro-lesson write-up for one skill gap.

    One call per skill in the background task _generate_byte_sized_lessons.
    Uses Haiku via the standard MultiTierModelClient — content quality is
    sufficient for Haiku; the structured output schema keeps it disciplined.
    max_tokens=2000 covers the full write-up plus links within NVIDIA budget.
    """

    name = "byte_sized_lesson"
    model = "claude-haiku-4-5-20251001"
    output_model = ByteSizedLessonOutput
    max_tokens = 2000

    def _build_messages(self, input: ByteSizedLessonInput) -> list[dict[str, Any]]:
        """Serialize the skill-gap context as a user message for the LLM."""
        gap_pct = round((1.0 - input.current_mastery_score) * 100, 1)
        target_pct = round(input.target_mastery_score * 100, 1)

        context: dict[str, Any] = {
            "skill_name": input.skill_name,
            "skill_description": input.skill_description,
            "current_mastery_score": round(input.current_mastery_score, 3),
            "current_gap_pct": gap_pct,
            "target_mastery_pct": target_pct,
            "certification_name": input.certification_name,
            "exam_domain": {
                "name": input.domain_name,
                "description": input.domain_description,
            },
        }

        return [
            {
                "role": "user",
                "content": (
                    f"## Byte-sized lesson request\n\n"
                    f"```json\n{json.dumps(context, indent=2)}\n```\n\n"
                    f"Generate a byte-sized lesson for the skill gap above. "
                    f"The practitioner is preparing for **{input.certification_name}**. "
                    f"Their current mastery is {round(input.current_mastery_score * 100, 0):.0f}% "
                    f"(gap: {gap_pct}%). "
                    f"Return all required fields in the structured output schema."
                ),
            }
        ]
