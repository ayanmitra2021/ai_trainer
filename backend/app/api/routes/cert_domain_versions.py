"""Phase 10.2 — Admin endpoints for certification domain versions and proposals.

Routes (all admin-only):
    GET /admin/cert-domain-versions          — list all version rows, newest first per cert
    GET /admin/cert-domain-proposals         — list proposals by status (default: pending_review)

These endpoints are the read side of the domain versioning system.
The write side (discover, approve, reject) is added in Step 10.3 when
the Cert Domain Discovery Agent is implemented.

All routes require the ``require_admin`` dependency — leadership sessions
receive 403.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.session import SessionInfo, require_admin
from app.db.models import (
    Certification,
    CertificationDomainProposal,
    CertificationDomainVersion,
)
from app.db.session import get_db
from app.schemas.cert_domain_versions import (
    CertificationDomainProposalRead,
    CertificationDomainVersionRead,
)

router = APIRouter(prefix="/admin", tags=["cert-domain-versions"])


@router.get(
    "/cert-domain-versions",
    response_model=list[CertificationDomainVersionRead],
    summary="List all certification domain versions (admin only)",
    description=(
        "Returns every ``certification_domain_versions`` row, ordered by "
        "certification code then ``created_at`` descending (newest first per cert). "
        "Use this to audit which version is current for each cert and inspect "
        "the version history before triggering a refresh."
    ),
)
async def list_cert_domain_versions(
    _session: SessionInfo = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[CertificationDomainVersionRead]:
    """List all domain version rows, newest first per certification."""
    result = await db.execute(
        select(CertificationDomainVersion, Certification.code)
        .join(
            Certification,
            CertificationDomainVersion.certification_id == Certification.id,
            isouter=True,  # outer join so orphaned versions still appear
        )
        .order_by(
            Certification.code.asc().nullslast(),
            CertificationDomainVersion.created_at.desc(),
        )
    )
    rows = result.all()

    return [
        CertificationDomainVersionRead(
            id=version.id,
            certification_id=version.certification_id,
            certification_code=cert_code,
            version_label=version.version_label,
            is_current=version.is_current,
            source_notes=version.source_notes,
            agent_run_id=version.agent_run_id,
            created_by_admin_id=version.created_by_admin_id,
            created_at=version.created_at,
        )
        for version, cert_code in rows
    ]


@router.get(
    "/cert-domain-proposals",
    response_model=list[CertificationDomainProposalRead],
    summary="List certification domain proposals (admin only)",
    description=(
        "Returns domain refresh proposals produced by the Cert Domain Discovery "
        "Agent.  By default, returns only ``pending_review`` proposals so the "
        "admin sees what needs action.  Pass ``?status=approved`` or "
        "``?status=rejected`` to inspect the history. "
        "Ordered by ``created_at`` descending (newest first)."
    ),
)
async def list_cert_domain_proposals(
    status: str | None = Query(
        default="pending_review",
        description=(
            "Filter by proposal status. "
            "One of: pending_review, approved, rejected. "
            "Omit to see all proposals."
        ),
        pattern="^(pending_review|approved|rejected)$",
    ),
    _session: SessionInfo = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[CertificationDomainProposalRead]:
    """List domain proposals, filtered by status."""
    stmt = select(CertificationDomainProposal).order_by(
        CertificationDomainProposal.created_at.desc()
    )
    if status is not None:
        stmt = stmt.where(CertificationDomainProposal.status == status)

    result = await db.execute(stmt)
    proposals = result.scalars().all()

    return [
        CertificationDomainProposalRead(
            id=p.id,
            certification_id=p.certification_id,
            cert_code=p.cert_code,
            cert_name=p.cert_name,
            proposed_domains=p.proposed_domains or [],
            source_notes=p.source_notes,
            agent_run_id=p.agent_run_id,
            status=p.status,
            reviewed_by_admin_id=p.reviewed_by_admin_id,
            reviewed_at=p.reviewed_at,
            rejection_notes=p.rejection_notes,
            created_at=p.created_at,
        )
        for p in proposals
    ]
