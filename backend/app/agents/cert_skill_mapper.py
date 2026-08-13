"""Cert Skill Mapper Agent — Phase 13.2.

Web-researches a certification's current exam blueprint and returns 10–12
overarching skills aligned to the cert's official exam domains.

Skills are upserted into certification_skills (and skills if new) with
domain linkage and source='agent_discovered'. Seed rows are never touched.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.agents.base import Agent


class CertSkillMapperDomain(BaseModel):
    domain_id: str
    domain_name: str
    domain_description: str
    weight_pct: float


class CertSkillMapperInput(BaseModel):
    cert_code: str
    cert_name: str
    cert_external_url: str | None = None
    domains: list[CertSkillMapperDomain]


class DiscoveredCertSkill(BaseModel):
    skill_name: str
    skill_description: str
    primary_domain_id: str  # must match one of the input domain_ids
    weight: float = Field(..., ge=0.0, le=1.0)
    rationale: str


class CertSkillMapperOutput(BaseModel):
    cert_code: str
    skills: list[DiscoveredCertSkill] = Field(..., min_length=1)
    source_notes: str
    confidence: Literal["high", "medium", "low"]


class CertSkillMapperAgent(Agent[CertSkillMapperInput, CertSkillMapperOutput]):
    """Maps a certification's exam blueprint to 10–12 skill graph nodes.

    Uses web-research style prompting (LLM training knowledge + provided domain
    context) to discover skills that collectively cover all exam domains.
    """

    name = "cert_skill_mapper"
    model = "claude-sonnet-5"
    output_model = CertSkillMapperOutput
    max_tokens = 6000

    def _build_messages(self, input: CertSkillMapperInput) -> list[dict[str, Any]]:
        context = {
            "cert_code": input.cert_code,
            "cert_name": input.cert_name,
            "cert_external_url": input.cert_external_url,
            "domains": [
                {
                    "domain_id": d.domain_id,
                    "domain_name": d.domain_name,
                    "domain_description": d.domain_description,
                    "weight_pct": d.weight_pct,
                }
                for d in input.domains
            ],
        }
        return [
            {
                "role": "user",
                "content": (
                    "## Cert skill mapping request\n\n"
                    f"```json\n{json.dumps(context, indent=2)}\n```\n\n"
                    "Research this certification's current exam blueprint and return "
                    "10–12 overarching skills aligned to its official exam domains. "
                    "Each skill must reference one of the domain_ids provided above.\n"
                    f"Return exactly one `cert_code` matching '{input.cert_code}'."
                ),
            }
        ]
