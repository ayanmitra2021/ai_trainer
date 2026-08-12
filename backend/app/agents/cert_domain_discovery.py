"""Cert Domain Discovery Agent — Step 10.3.

LLM-driven exam domain research & refresh.  Given a certification code, name,
and provider, the agent researches current official exam domains / weights and
returns structured proposals for admin review.

Proposals are never written directly to certification_domains — they land in
certification_domain_proposals (status=pending_review) and require admin
approval before any version rows or domain rows are created.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.agents.base import Agent


class ProposedDomain(BaseModel):
    sequence_order: int
    domain_name: str
    domain_description: str
    weight_pct: float


class CertDomainDiscoveryInput(BaseModel):
    cert_code: str
    cert_name: str
    provider_name: str
    known_source_url: str | None = None
    current_domains: list[dict] | None = None  # [{domain_name, weight_pct}]
    refresh_reason: str | None = None


class CertDomainDiscoveryOutput(BaseModel):
    cert_code: str
    proposed_domains: list[ProposedDomain]
    source_notes: str
    changes_from_current: list[str] | None = None
    confidence: Literal["high", "medium", "low"]
    suggested_source_url: str | None = None


class CertDomainDiscoveryAgent(Agent[CertDomainDiscoveryInput, CertDomainDiscoveryOutput]):
    name = "cert_domain_discovery"
    model = "claude-sonnet-5"
    output_model = CertDomainDiscoveryOutput

    def _build_messages(self, input: CertDomainDiscoveryInput) -> list[dict[str, Any]]:
        context = {
            "cert_code": input.cert_code,
            "cert_name": input.cert_name,
            "provider_name": input.provider_name,
            "known_source_url": input.known_source_url,
            "current_domains": input.current_domains,
            "refresh_reason": input.refresh_reason,
        }
        return [
            {
                "role": "user",
                "content": (
                    "## Certification domain discovery request\n\n"
                    f"```json\n{json.dumps(context, indent=2)}\n```\n\n"
                    "Please research and propose updated exam domain definitions "
                    "for this certification."
                ),
            }
        ]
