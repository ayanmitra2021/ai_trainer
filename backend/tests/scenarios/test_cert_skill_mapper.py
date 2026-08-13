"""Phase 13.2 — CertSkillMapperAgent scenario tests."""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.cert_skill_mapper import (
    CertSkillMapperAgent,
    CertSkillMapperInput,
    CertSkillMapperDomain,
)
from app.db.models import (
    Certification,
    CertificationDomain,
    CertificationDomainVersion,
    CertificationProvider,
    CertificationSkill,
    Skill,
)
from app.services.cert_skill_mapper_service import persist_cert_skill_mapping
from tests.fixtures.stub_claude_client import StubClaudeClient


def _make_stub(cert_code: str, domain_ids: list[str], n_skills: int = 10) -> StubClaudeClient:
    skills = []
    for i in range(n_skills):
        domain_id = domain_ids[i % len(domain_ids)]
        skills.append({
            "skill_name": f"Discovered Skill {i + 1}",
            "skill_description": f"Description for discovered skill {i + 1}.",
            "primary_domain_id": domain_id,
            "weight": 0.7,
            "rationale": f"Skill {i + 1} covers key knowledge areas in domain {domain_id}.",
        })
    return StubClaudeClient(response_data={
        "cert_code": cert_code,
        "skills": skills,
        "source_notes": "Based on official exam guide. Verified via training data.",
        "confidence": "high",
    })


@pytest_asyncio.fixture
async def cert_with_domains(db_session: AsyncSession):
    provider = CertificationProvider(
        id=str(uuid.uuid4()), name="Test Provider CS", website=None
    )
    db_session.add(provider)
    await db_session.flush()

    cert = Certification(
        id=str(uuid.uuid4()),
        provider_id=provider.id,
        code="TEST-CS",
        name="Test Cert for Skill Mapper",
        level="foundational",
        requires_coding_background=False,
        is_active=True,
    )
    db_session.add(cert)
    await db_session.flush()

    version = CertificationDomainVersion(
        id=str(uuid.uuid4()),
        certification_id=cert.id,
        version_label="bootstrap",
        is_current=True,
        source_notes="test",
    )
    db_session.add(version)
    await db_session.flush()

    domains = []
    for i in range(5):
        d = CertificationDomain(
            id=str(uuid.uuid4()),
            certification_id=cert.id,
            domain_version_id=version.id,
            domain_name=f"Domain {i + 1}",
            domain_description=f"Description for domain {i + 1}.",
            weight_pct=20.0,
            sequence_order=i + 1,
        )
        db_session.add(d)
        domains.append(d)
    await db_session.flush()

    return cert, domains


class TestCertSkillMapperAgent:
    async def test_maps_10_skills_with_domain_linkage(
        self,
        db_session: AsyncSession,
        cert_with_domains,
    ):
        """
        Scenario: Agent maps 10 discovered skills to cert domains.
          Given a cert with 5 domains and a stub response of 10 skills
          When persist_cert_skill_mapping is called with the agent output
          Then 10 certification_skills rows exist with source='agent_discovered'
            and each row has a non-null certification_domain_id
            and the skills table has rows for each discovered skill name
        """
        cert, domains = cert_with_domains
        domain_ids = [d.id for d in domains]
        stub = _make_stub(cert.code, domain_ids, n_skills=10)

        mapper_input = CertSkillMapperInput(
            cert_code=cert.code,
            cert_name=cert.name,
            domains=[
                CertSkillMapperDomain(
                    domain_id=d.id,
                    domain_name=d.domain_name,
                    domain_description=d.domain_description,
                    weight_pct=float(d.weight_pct),
                )
                for d in domains
            ],
        )
        agent = CertSkillMapperAgent(client=stub, db_session=db_session)
        output = await agent.run(mapper_input)

        await persist_cert_skill_mapping(
            cert_id=cert.id,
            agent_run_id="",
            output=output,
            db=db_session,
        )

        # 10 agent_discovered rows
        result = await db_session.execute(
            select(CertificationSkill).where(
                CertificationSkill.certification_id == cert.id,
                CertificationSkill.source == "agent_discovered",
            )
        )
        rows = result.scalars().all()
        assert len(rows) == 10

        # Each row has a domain_id from our domains
        for row in rows:
            assert row.certification_domain_id is not None
            assert row.certification_domain_id in domain_ids

        # Skills table has the discovered skill names
        skill_result = await db_session.execute(select(Skill))
        all_skills = {s.name for s in skill_result.scalars().all()}
        for i in range(10):
            assert f"Discovered Skill {i + 1}" in all_skills

    async def test_reruns_replaces_agent_discovered_skills(
        self,
        db_session: AsyncSession,
        cert_with_domains,
    ):
        """
        Scenario: Re-running discovery replaces previous agent_discovered skills.
          Given 10 existing agent_discovered skills for a cert
          When CertSkillMapperAgent is called again with a 12-skill response
          Then exactly 12 agent_discovered rows exist (old 10 replaced)
            and seed rows (source='seed') are untouched
        """
        cert, domains = cert_with_domains
        domain_ids = [d.id for d in domains]

        # Pre-seed a SEED row to verify it's never touched
        seed_skill = Skill(
            id=str(uuid.uuid4()), name="Seed Skill Alpha", category="Test"
        )
        db_session.add(seed_skill)
        await db_session.flush()
        db_session.add(CertificationSkill(
            certification_id=cert.id,
            skill_id=seed_skill.id,
            weight=0.8,
            source="seed",
        ))
        await db_session.flush()

        # First run: 10 skills
        stub10 = _make_stub(cert.code, domain_ids, n_skills=10)
        agent = CertSkillMapperAgent(client=stub10, db_session=db_session)
        out10 = await agent.run(CertSkillMapperInput(
            cert_code=cert.code, cert_name=cert.name,
            domains=[CertSkillMapperDomain(
                domain_id=d.id, domain_name=d.domain_name,
                domain_description=d.domain_description, weight_pct=float(d.weight_pct),
            ) for d in domains],
        ))
        await persist_cert_skill_mapping(cert.id, "", out10, db_session)

        # Second run: 12 skills
        stub12 = _make_stub(cert.code, domain_ids, n_skills=12)
        agent2 = CertSkillMapperAgent(client=stub12, db_session=db_session)
        out12 = await agent2.run(CertSkillMapperInput(
            cert_code=cert.code, cert_name=cert.name,
            domains=[CertSkillMapperDomain(
                domain_id=d.id, domain_name=d.domain_name,
                domain_description=d.domain_description, weight_pct=float(d.weight_pct),
            ) for d in domains],
        ))
        await persist_cert_skill_mapping(cert.id, "", out12, db_session)

        # Exactly 12 agent_discovered rows
        ad_result = await db_session.execute(
            select(CertificationSkill).where(
                CertificationSkill.certification_id == cert.id,
                CertificationSkill.source == "agent_discovered",
            )
        )
        assert len(ad_result.scalars().all()) == 12

        # Seed row is still there
        seed_result = await db_session.execute(
            select(CertificationSkill).where(
                CertificationSkill.certification_id == cert.id,
                CertificationSkill.source == "seed",
            )
        )
        assert len(seed_result.scalars().all()) == 1
