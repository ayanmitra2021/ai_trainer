"""Certification Advisor Agent — Step 2.3.

Matches a short questionnaire to the best-fit certification in the current
catalog. Returns a typed AdvisorOutput; callers persist results to DB.

👤 Review prompts/certification_advisor.md before trusting at scale.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from app.agents.base import Agent
from app.schemas.certifications import (
    AdvisorOutput,
    CertificationContext,
    QuestionnaireAnswers,
)


class CertificationAdvisorInput(BaseModel):
    """Input to the Certification Advisor agent."""

    practitioner_id: str
    answers: QuestionnaireAnswers
    catalog: list[CertificationContext]


class CertificationAdvisorAgent(Agent[CertificationAdvisorInput, AdvisorOutput]):
    """Recommends a certification from the catalog based on questionnaire answers."""

    name = "certification_advisor"
    model = "claude-sonnet-5"
    output_model = AdvisorOutput

    def _build_messages(self, input: CertificationAdvisorInput) -> list[dict[str, Any]]:
        # Catalog is passed as structured data in the user message — not baked
        # into the prompt — so newly-added or retired certs take effect immediately.
        catalog_json = json.dumps(
            [c.model_dump() for c in input.catalog], indent=2
        )
        answers_json = json.dumps(input.answers.model_dump(), indent=2)

        return [
            {
                "role": "user",
                "content": (
                    f"## Current certification catalog\n\n```json\n{catalog_json}\n```\n\n"
                    f"## Practitioner questionnaire answers\n\n```json\n{answers_json}\n```\n\n"
                    "Please recommend the best-fit certification for this practitioner."
                ),
            }
        ]
