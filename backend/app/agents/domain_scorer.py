"""Domain Scorer Agent — Step 10.5.

Maps self-assessment proficiency ratings to initial certification domain scores
at profile-lock time.  The output is capped at 0.5 for both initial_score and
confidence — these are estimates, not measured performance.  Quiz-derived scores
(from cert-evaluated quiz answers) are never overwritten by this agent.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from app.agents.base import Agent


class DomainScoreItem(BaseModel):
    certification_domain_id: str
    initial_score: float = Field(..., ge=0.0, le=0.5)  # capped at 0.5 — estimate only
    confidence: float = Field(..., ge=0.0, le=0.5)
    rationale: str


class DomainScorerInput(BaseModel):
    certification_id: str
    certification_domains: list[dict]  # [{id, name, description, weight_pct}]
    skill_assessments: list[dict]     # [{skill_name, signal_strength}]


class DomainScorerOutput(BaseModel):
    domain_scores: list[DomainScoreItem]


class DomainScorerAgent(Agent[DomainScorerInput, DomainScorerOutput]):
    name = "domain_scorer"
    model = "claude-sonnet-5"
    output_model = DomainScorerOutput

    def _build_messages(self, input: DomainScorerInput) -> list[dict[str, Any]]:
        context = {
            "certification_id": input.certification_id,
            "certification_domains": input.certification_domains,
            "skill_assessments": input.skill_assessments,
        }
        return [
            {
                "role": "user",
                "content": (
                    "## Domain scoring request\n\n"
                    f"```json\n{json.dumps(context, indent=2)}\n```\n\n"
                    "Based on these self-assessment skill ratings, estimate initial "
                    "domain readiness scores for each exam domain."
                ),
            }
        ]
