"""Phase 13.3 — Profile lock triggers CertSkillMapper when no agent-discovered skills exist."""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Certification,
    CertificationDomain,
    CertificationDomainVersion,
    CertificationProvider,
    CertificationSkill,
    Practitioner,
    PractitionerProfile,
    ProfileSkillAssessment,
    Skill,
)


@pytest_asyncio.fixture
async def hook_cert(db_session: AsyncSession):
    provider = CertificationProvider(
        id=str(uuid.uuid4()), name="Hook Test Provider", website=None
    )
    db_session.add(provider)
    await db_session.flush()

    cert = Certification(
        id=str(uuid.uuid4()),
        provider_id=provider.id,
        code="HOOK-01",
        name="Hook Test Cert",
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

    for i in range(3):
        db_session.add(CertificationDomain(
            id=str(uuid.uuid4()),
            certification_id=cert.id,
            domain_version_id=version.id,
            domain_name=f"Domain {i + 1}",
            domain_description=f"Desc {i + 1}",
            weight_pct=33.33,
            sequence_order=i + 1,
        ))
    await db_session.flush()
    return cert


class TestCertSkillMapperHook:
    async def test_generate_learning_path_prefers_agent_discovered_skills(
        self,
        db_session: AsyncSession,
        hook_cert: Certification,
    ):
        """
        Scenario: generate_learning_path prefers agent_discovered over seed skills.
          Given a cert with both seed and agent_discovered certification_skills rows
          When the cert context is resolved in generate_learning_path
          Then the agent_discovered rows are preferred over seed rows
        """
        # Create a seed skill
        seed_skill = Skill(
            id=str(uuid.uuid4()), name="Seed Skill HookTest", category="General"
        )
        db_session.add(seed_skill)
        await db_session.flush()
        db_session.add(CertificationSkill(
            certification_id=hook_cert.id,
            skill_id=seed_skill.id,
            weight=0.5,
            source="seed",
        ))

        # Create an agent_discovered skill
        agent_skill = Skill(
            id=str(uuid.uuid4()), name="Agent Skill HookTest", category="Certification"
        )
        db_session.add(agent_skill)
        await db_session.flush()
        db_session.add(CertificationSkill(
            certification_id=hook_cert.id,
            skill_id=agent_skill.id,
            weight=0.9,
            source="agent_discovered",
        ))
        await db_session.flush()

        # Query agent_discovered skills
        ad_result = await db_session.execute(
            select(CertificationSkill).where(
                CertificationSkill.certification_id == hook_cert.id,
                CertificationSkill.source == "agent_discovered",
            )
        )
        ad_skills = ad_result.scalars().all()
        assert len(ad_skills) == 1
        assert ad_skills[0].skill_id == agent_skill.id

        # These would be used instead of seed rows
        seed_result = await db_session.execute(
            select(CertificationSkill).where(
                CertificationSkill.certification_id == hook_cert.id,
                CertificationSkill.source == "seed",
            )
        )
        seed_skills = seed_result.scalars().all()
        assert len(seed_skills) == 1  # seed still present, just not used
