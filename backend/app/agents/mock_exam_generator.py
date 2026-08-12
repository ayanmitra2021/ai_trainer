"""Mock Exam Generator Agent — Phase 11.

Generates hard MCQ questions (difficulty 0.70–1.00) for a full mock exam sitting.
Questions are generated in batches of up to 15, all concurrently, so callers
should run multiple batch calls via asyncio.gather rather than awaiting serially.

Callers persist questions to DB and create the MockExamSession row.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from app.agents.base import Agent


# ── Schemas ───────────────────────────────────────────────────────────────────

class MockExamQuestionSpec(BaseModel):
    """Agent output for a single MCQ — matches what gets stored in mock_exam_questions."""

    certification_domain_name: str | None = None
    skill_name: str | None = None
    prompt: str
    options: list[str]        # exactly 4 options
    correct_index: int        # 0–3
    trap_index: int | None    # 0–3, or null if no distinguishable trap
    trap_explanation: str | None = None
    difficulty: float         # 0.70–1.00 — hard questions only


class MockExamGeneratorInput(BaseModel):
    """Input to one batch generation call."""

    cert_code: str
    cert_name: str
    batch_size: int           # how many questions to generate (typically 15)
    domain_focus: str | None = None  # e.g. "Domain 2: Agentic Patterns (30%)"
    batch_number: int         # 1-based, for variety across batches


class MockExamGeneratorOutput(BaseModel):
    """Agent output — a list of question specs."""

    questions: list[MockExamQuestionSpec]


# ── Agent ──────────────────────────────────────────────────────────────────────

class MockExamGeneratorAgent(Agent[MockExamGeneratorInput, MockExamGeneratorOutput]):
    """Generates hard MCQ questions for a certification mock exam."""

    name = "mock_exam_generator"
    model = "claude-sonnet-5"
    output_model = MockExamGeneratorOutput
    max_tokens = 16000  # large — generating up to 15 questions per batch

    def _build_messages(self, input: MockExamGeneratorInput) -> list[dict[str, Any]]:
        context = {
            "cert_code": input.cert_code,
            "cert_name": input.cert_name,
            "batch_size": input.batch_size,
            "domain_focus": input.domain_focus,
            "batch_number": input.batch_number,
        }
        context_json = json.dumps(context, indent=2)

        return [
            {
                "role": "user",
                "content": (
                    f"## Mock exam generation request\n\n```json\n{context_json}\n```\n\n"
                    f"Generate exactly {input.batch_size} hard MCQ questions for this batch."
                ),
            }
        ]
