"""Pydantic schemas for Phase 10.2 — domain versioning API responses.

Covers:
- CertificationDomainVersionRead — one version row with cert code joined in
- CertificationDomainProposalRead — one proposal row as returned by the API

These schemas are returned by the admin-only endpoints:
    GET /admin/cert-domain-versions
    GET /admin/cert-domain-proposals
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
