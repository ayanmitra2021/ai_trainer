"""Phase 10.2/10.3 — Admin endpoints for certification domain versions and proposals.

Routes (all admin-only):
    GET  /admin/cert-domain-versions                     — list version rows, newest first per cert
    GET  /admin/cert-domain-proposals                    — list proposals by status
    POST /admin/cert-domains/discover                    — run discovery agent for one cert
    POST /admin/cert-domains/discover-all               — run discovery for all active certs
    POST /admin/cert-domain-proposals/{id}/approve      — approve a proposal, create new version
    POST /admin/cert-domain-proposals/{id}/reject       — reject a proposal

All routes require the ``require_admin`` dependency — leadership sessions
receive 403.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.cert_domain_discovery import (
    CertDomainDiscoveryAgent,
    CertDomainDiscoveryInput,
)
from app.agents.model_client import create_model_client
from app.api.deps.session import SessionInfo, require_admin
from app.db.models import (
    Certification,
    CertificationDomain,
    CertificationDomainProposal,
    CertificationDomainVersion,
    CertificationProvider,
)
from app.db.session import get_db
from app.schemas.cert_domain_versions import (
    ApproveProposalResponse,
    CertDomainDiscoverRequest,
    CertificationDomainProposalRead,
    CertificationDomainVersionRead,
    RejectProposalRequest,
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


# ── Step 10.3 — discover / approve / reject endpoints ─────────────────────────


async def _run_discovery_for_cert(
    cert: Certification,
    provider_name: str,
    refresh_reason: str | None,
    known_source_url: str | None,
    admin_session: SessionInfo,
    db: AsyncSession,
) -> CertificationDomainProposal:
    """Run the Cert Domain Discovery Agent for one cert and persist the proposal."""
    # Build current domains list for the agent context
    current_domains_result = await db.execute(
        select(CertificationDomain)
        .where(CertificationDomain.certification_id == cert.id)
        .order_by(CertificationDomain.sequence_order)
    )
    current_domains = [
        {"domain_name": d.domain_name, "weight_pct": float(d.weight_pct)}
        for d in current_domains_result.scalars().all()
    ]

    model_client = create_model_client()
    agent = CertDomainDiscoveryAgent(client=model_client, db_session=db)

    discovery_input = CertDomainDiscoveryInput(
        cert_code=cert.code,
        cert_name=cert.name,
        provider_name=provider_name,
        known_source_url=known_source_url or cert.external_url,
        current_domains=current_domains or None,
        refresh_reason=refresh_reason,
    )
    output = await agent.run(discovery_input)

    # Find the agent_run row that was just written (most recent for this agent)
    from app.db.models import AgentRun
    agent_run_result = await db.execute(
        select(AgentRun)
        .where(AgentRun.agent_name == "cert_domain_discovery")
        .order_by(AgentRun.started_at.desc())
        .limit(1)
    )
    agent_run = agent_run_result.scalar_one_or_none()
    if agent_run is None:
        raise HTTPException(status_code=500, detail="Agent run row not found after agent.run()")

    # Persist the proposal
    proposal = CertificationDomainProposal(
        id=str(uuid.uuid4()),
        certification_id=cert.id,
        cert_code=cert.code,
        cert_name=cert.name,
        proposed_domains=[d.model_dump() for d in output.proposed_domains],
        source_notes=output.source_notes,
        agent_run_id=agent_run.id,
        status="pending_review",
    )
    db.add(proposal)
    await db.flush()
    return proposal


@router.post(
    "/cert-domains/discover",
    response_model=CertificationDomainProposalRead,
    status_code=201,
    summary="Run domain discovery for one certification (admin only)",
)
async def discover_cert_domains(
    body: CertDomainDiscoverRequest,
    session: SessionInfo = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> CertificationDomainProposalRead:
    """Run the Cert Domain Discovery Agent for one cert and create a pending proposal."""
    # Look up existing cert by code
    cert_result = await db.execute(
        select(Certification).where(Certification.code == body.cert_code)
    )
    cert = cert_result.scalar_one_or_none()

    if cert is None:
        # Create a stub cert so we can attach the proposal to it later
        # Look up or create provider
        provider_result = await db.execute(
            select(CertificationProvider).where(
                CertificationProvider.name == body.provider_name
            )
        )
        provider = provider_result.scalar_one_or_none()
        if provider is None:
            provider = CertificationProvider(
                id=str(uuid.uuid4()),
                name=body.provider_name,
            )
            db.add(provider)
            await db.flush()

        cert = Certification(
            id=str(uuid.uuid4()),
            provider_id=provider.id,
            code=body.cert_code,
            name=body.cert_name,
            level="foundational",
            requires_coding_background=False,
            is_active=False,  # inactive until admin explicitly activates
        )
        db.add(cert)
        await db.flush()

    # Get provider name
    provider = await db.get(CertificationProvider, cert.provider_id)
    provider_name = provider.name if provider else body.provider_name

    proposal = await _run_discovery_for_cert(
        cert=cert,
        provider_name=provider_name,
        refresh_reason=body.refresh_reason,
        known_source_url=body.known_source_url,
        admin_session=session,
        db=db,
    )
    await db.commit()

    return CertificationDomainProposalRead(
        id=proposal.id,
        certification_id=proposal.certification_id,
        cert_code=proposal.cert_code,
        cert_name=proposal.cert_name,
        proposed_domains=proposal.proposed_domains or [],
        source_notes=proposal.source_notes,
        agent_run_id=proposal.agent_run_id,
        status=proposal.status,
        reviewed_by_admin_id=proposal.reviewed_by_admin_id,
        reviewed_at=proposal.reviewed_at,
        rejection_notes=proposal.rejection_notes,
        created_at=proposal.created_at,
    )


@router.post(
    "/cert-domains/discover-all",
    response_model=list[CertificationDomainProposalRead],
    status_code=201,
    summary="Run domain discovery for all active certifications (admin only)",
)
async def discover_all_cert_domains(
    refresh_reason: str | None = Query(default=None),
    session: SessionInfo = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[CertificationDomainProposalRead]:
    """Run the Cert Domain Discovery Agent for every active certification."""
    certs_result = await db.execute(
        select(Certification).where(Certification.is_active == True)  # noqa: E712
    )
    certs = certs_result.scalars().all()

    proposals_out: list[CertificationDomainProposalRead] = []
    for cert in certs:
        provider = await db.get(CertificationProvider, cert.provider_id)
        provider_name = provider.name if provider else "Unknown"
        proposal = await _run_discovery_for_cert(
            cert=cert,
            provider_name=provider_name,
            refresh_reason=refresh_reason,
            known_source_url=cert.external_url,
            admin_session=session,
            db=db,
        )
        proposals_out.append(
            CertificationDomainProposalRead(
                id=proposal.id,
                certification_id=proposal.certification_id,
                cert_code=proposal.cert_code,
                cert_name=proposal.cert_name,
                proposed_domains=proposal.proposed_domains or [],
                source_notes=proposal.source_notes,
                agent_run_id=proposal.agent_run_id,
                status=proposal.status,
                reviewed_by_admin_id=proposal.reviewed_by_admin_id,
                reviewed_at=proposal.reviewed_at,
                rejection_notes=proposal.rejection_notes,
                created_at=proposal.created_at,
            )
        )

    await db.commit()
    return proposals_out


@router.post(
    "/cert-domain-proposals/{proposal_id}/approve",
    response_model=ApproveProposalResponse,
    summary="Approve a domain refresh proposal (admin only)",
)
async def approve_proposal(
    proposal_id: str,
    session: SessionInfo = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ApproveProposalResponse:
    """Approve a pending domain proposal: flip old version, create new version + domains."""
    proposal = await db.get(CertificationDomainProposal, proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if proposal.status != "pending_review":
        raise HTTPException(
            status_code=400,
            detail=f"Proposal is already '{proposal.status}', not pending_review",
        )

    now = datetime.now(UTC)
    new_cert_created = False

    # Get or create certification
    cert: Certification | None = None
    if proposal.certification_id is not None:
        cert = await db.get(Certification, proposal.certification_id)

    if cert is None:
        # Proposal for a new cert — look up by code first
        cert_result = await db.execute(
            select(Certification).where(Certification.code == proposal.cert_code)
        )
        cert = cert_result.scalar_one_or_none()

    if cert is None:
        # Create a placeholder cert with is_active=False
        # Try to find a provider or create a default one
        provider_result = await db.execute(
            select(CertificationProvider).limit(1)
        )
        provider = provider_result.scalar_one_or_none()
        if provider is None:
            provider = CertificationProvider(
                id=str(uuid.uuid4()),
                name="Unknown Provider",
            )
            db.add(provider)
            await db.flush()

        cert = Certification(
            id=str(uuid.uuid4()),
            provider_id=provider.id,
            code=proposal.cert_code,
            name=proposal.cert_name,
            level="foundational",
            requires_coding_background=False,
            is_active=False,  # admin must explicitly activate
        )
        db.add(cert)
        await db.flush()
        new_cert_created = True

        # Update proposal to link to the new cert
        proposal.certification_id = cert.id

    # Flip all existing is_current=True versions for this cert to False
    await db.execute(
        update(CertificationDomainVersion)
        .where(
            CertificationDomainVersion.certification_id == cert.id,
            CertificationDomainVersion.is_current == True,  # noqa: E712
        )
        .values(is_current=False)
    )
    await db.flush()

    # Create new version row
    version_label = f"{now.strftime('%Y-%m-%d')}-refresh"
    new_version = CertificationDomainVersion(
        id=str(uuid.uuid4()),
        certification_id=cert.id,
        version_label=version_label,
        is_current=True,
        source_notes=proposal.source_notes,
        agent_run_id=proposal.agent_run_id,
        created_by_admin_id=session.admin_user_id,
        created_at=now,
    )
    db.add(new_version)
    await db.flush()

    # Create new certification_domain rows from the proposal
    domains_created = 0
    for domain_data in (proposal.proposed_domains or []):
        domain = CertificationDomain(
            id=str(uuid.uuid4()),
            certification_id=cert.id,
            domain_version_id=new_version.id,
            domain_name=domain_data.get("domain_name", ""),
            domain_description=domain_data.get("domain_description", ""),
            weight_pct=domain_data.get("weight_pct", 0.0),
            sequence_order=domain_data.get("sequence_order", domains_created + 1),
        )
        db.add(domain)
        domains_created += 1

    # Mark proposal as approved
    proposal.status = "approved"
    proposal.reviewed_by_admin_id = session.admin_user_id
    proposal.reviewed_at = now

    await db.commit()

    return ApproveProposalResponse(
        proposal_id=proposal_id,
        new_version_id=new_version.id,
        cert_code=cert.code,
        domains_created=domains_created,
        new_cert_created=new_cert_created,
    )


@router.post(
    "/cert-domain-proposals/{proposal_id}/reject",
    status_code=200,
    summary="Reject a domain refresh proposal (admin only)",
)
async def reject_proposal(
    proposal_id: str,
    body: RejectProposalRequest,
    session: SessionInfo = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Reject a pending domain proposal with a note. certification_domains rows are untouched."""
    proposal = await db.get(CertificationDomainProposal, proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if proposal.status != "pending_review":
        raise HTTPException(
            status_code=400,
            detail=f"Proposal is already '{proposal.status}', not pending_review",
        )

    now = datetime.now(UTC)
    proposal.status = "rejected"
    proposal.rejection_notes = body.rejection_notes
    proposal.reviewed_by_admin_id = session.admin_user_id
    proposal.reviewed_at = now

    await db.commit()
    return {"proposal_id": proposal_id, "status": "rejected"}
