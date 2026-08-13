"""Phase 13.2 — Admin endpoints for cert skill discovery.

Routes:
  POST /admin/certs/{cert_id}/discover-skills   Run CertSkillMapperAgent for a cert
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.cert_skill_mapper import CertSkillMapperAgent, CertSkillMapperInput, CertSkillMapperDomain
from app.agents.model_client import create_model_client
from app.api.deps.session import SessionInfo, require_admin
from app.db.models import Certification, CertificationDomain, CertificationDomainVersion
from app.db.session import get_db
from app.services.cert_skill_mapper_service import persist_cert_skill_mapping

router = APIRouter(tags=["cert_discovery"])


@router.post("/admin/certs/{cert_id}/discover-skills")
async def discover_cert_skills(
    cert_id: str,
    db: AsyncSession = Depends(get_db),
    _session: SessionInfo = Depends(require_admin),
) -> dict:
    """Run CertSkillMapperAgent for a certification and persist discovered skills.

    Replaces all agent_discovered certification_skills rows for this cert.
    Seed rows are untouched.
    """
    cert = await db.get(Certification, cert_id)
    if cert is None:
        raise HTTPException(status_code=404, detail="Certification not found")

    # Get current domain version's domains
    version_result = await db.execute(
        select(CertificationDomainVersion).where(
            CertificationDomainVersion.certification_id == cert_id,
            CertificationDomainVersion.is_current == True,  # noqa: E712
        )
    )
    current_version = version_result.scalar_one_or_none()

    if current_version is None:
        raise HTTPException(
            status_code=422,
            detail="No current domain version found for this certification. "
                   "Seed domain data first via the domain seeder.",
        )

    domains_result = await db.execute(
        select(CertificationDomain).where(
            CertificationDomain.certification_id == cert_id,
            CertificationDomain.domain_version_id == current_version.id,
        ).order_by(CertificationDomain.sequence_order)
    )
    cert_domains = domains_result.scalars().all()

    if not cert_domains:
        raise HTTPException(
            status_code=422,
            detail="No exam domains found for this certification version. "
                   "Seed domain data before running skill discovery.",
        )

    mapper_input = CertSkillMapperInput(
        cert_code=cert.code,
        cert_name=cert.name,
        cert_external_url=cert.external_url,
        domains=[
            CertSkillMapperDomain(
                domain_id=d.id,
                domain_name=d.domain_name,
                domain_description=d.domain_description,
                weight_pct=float(d.weight_pct),
            )
            for d in cert_domains
        ],
    )

    model_client = create_model_client()
    agent = CertSkillMapperAgent(client=model_client, db_session=db)
    output = await agent.run(mapper_input)

    summary = await persist_cert_skill_mapping(
        cert_id=cert_id,
        agent_run_id="",  # agent_run_id tracked internally by base Agent
        output=output,
        db=db,
    )
    await db.commit()

    return {
        "skills_created": summary["skills_created"],
        "skills_matched": summary["skills_matched"],
        "source_notes": output.source_notes,
        "confidence": output.confidence,
        "total_skills": len(output.skills),
    }
