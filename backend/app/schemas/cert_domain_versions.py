"""Pydantic schemas for Phase 10.2/10.3 — domain versioning API responses.

Covers:
- CertificationDomainVersionRead — one version row with cert code joined in
- CertificationDomainProposalRead — one proposal row as returned by the API
- CertDomainDiscoverRequest — request body for the discover endpoint
- ApproveProposalResponse — response from approving a proposal
- RejectProposalRequest — request body for rejecting a proposal
- CertificationDomainScoreRead — per-domain readiness score for a practitioner
- QuizItemRead — extended ItemRead with domain awareness for quiz endpoint
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class CertificationDomainVersionRead(BaseModel):
    """One domain version snapshot, with cert code joined in for readability."""

    id: str
    certification_id: str
    # Joined from the Certification row — None only if the cert was deleted
    # (shouldn't happen in practice given the CASCADE FK)
    certification_code: str | None
    version_label: str
    is_current: bool
    source_notes: str
    agent_run_id: str | None
    created_by_admin_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CertificationDomainProposalRead(BaseModel):
    """One pending (or reviewed) domain refresh proposal."""

    id: str
    # null when proposing a brand-new cert not yet in the catalog
    certification_id: str | None
    cert_code: str
    cert_name: str
    # List of {sequence_order, domain_name, domain_description, weight_pct}
    proposed_domains: list[dict[str, Any]]
    source_notes: str
    agent_run_id: str
    # pending_review | approved | rejected
    status: str
    reviewed_by_admin_id: str | None
    reviewed_at: datetime | None
    rejection_notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Step 10.3 — discover / approve / reject schemas ───────────────────────────


class CertDomainDiscoverRequest(BaseModel):
    """Request body for POST /admin/cert-domains/discover."""

    cert_code: str
    cert_name: str
    provider_name: str
    known_source_url: str | None = None
    refresh_reason: str | None = None


class ApproveProposalResponse(BaseModel):
    """Response when an admin approves a domain refresh proposal."""

    proposal_id: str
    new_version_id: str
    cert_code: str
    domains_created: int
    new_cert_created: bool  # True if a new Certification row was created (is_active=False)


class RejectProposalRequest(BaseModel):
    """Request body for POST /admin/cert-domain-proposals/{id}/reject."""

    rejection_notes: str


class CertificationDomainScoreRead(BaseModel):
    """Per-domain readiness score for a practitioner, with trend info."""

    id: str
    certification_domain_id: str
    domain_name: str
    weight_pct: float
    sequence_order: int
    mastery_score: float
    confidence: float
    source: str  # self_assessment_estimate | quiz_derived
    last_computed_at: datetime
    previous_mastery_score: float | None = None
    mastery_delta: float | None = None
    trend: str = "new"  # improving | declining | stable | new

    model_config = {"from_attributes": True}


class QuizItemRead(BaseModel):
    """Extended ItemRead with domain awareness for the quiz endpoint."""

    id: str
    skill_id: str
    item_type: str
    prompt: str
    answer_key: dict
    trap_explanation: str | None
    difficulty: float
    certification_domain_id: str | None = None
    is_cert_evaluated: bool = False
    certification_domain_name: str | None = None
    generation: int = 1
    generation_refreshed: bool = False  # True if a freshly generated round was created
    new_generation: int | None = None

    model_config = {"from_attributes": True}
