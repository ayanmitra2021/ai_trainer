"""Service for persisting CertSkillMapper output to the database.

Business rules:
1. For each discovered skill, resolve or create a row in the `skills` table
   (match by name, case-insensitive; create if new).
2. Delete all existing agent_discovered rows for this cert — they are replaced
   each run. Seed rows (source='seed') are never touched.
3. Insert new CertificationSkill rows with source='agent_discovered' and the
   certification_domain_id resolved from the output's primary_domain_id.

Returns a summary dict: {skills_created, skills_matched, confidence}.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.cert_skill_mapper import CertSkillMapperOutput
from app.db.models import CertificationSkill, Skill

_log = logging.getLogger(__name__)


async def persist_cert_skill_mapping(
    cert_id: str,
    agent_run_id: str,
    output: CertSkillMapperOutput,
    db: AsyncSession,
) -> dict:
    """Persist a CertSkillMapperOutput to the database.

    Returns {skills_created, skills_matched, confidence}.
    """
    # 1. Resolve or create each skill in the `skills` table (case-insensitive match).
    skills_created = 0
    skills_matched = 0
    resolved: dict[str, str] = {}  # skill_name (lower) → skill_id

    for discovered in output.skills:
        name_lower = discovered.skill_name.strip().lower()

        existing_result = await db.execute(
            select(Skill).where(
                Skill.name.ilike(discovered.skill_name.strip())
            ).limit(1)
        )
        existing_skill = existing_result.scalar_one_or_none()

        if existing_skill is not None:
            resolved[name_lower] = existing_skill.id
            skills_matched += 1
        else:
            new_skill = Skill(
                id=str(uuid.uuid4()),
                name=discovered.skill_name.strip(),
                description=discovered.skill_description,
                category="Certification",  # default category for discovered skills
            )
            db.add(new_skill)
            await db.flush()
            resolved[name_lower] = new_skill.id
            skills_created += 1

    # 2. Delete all existing agent_discovered rows for this cert.
    await db.execute(
        delete(CertificationSkill).where(
            CertificationSkill.certification_id == cert_id,
            CertificationSkill.source == "agent_discovered",
        )
    )
    await db.flush()

    # 3. Insert new CertificationSkill rows.
    for discovered in output.skills:
        name_lower = discovered.skill_name.strip().lower()
        skill_id = resolved.get(name_lower)
        if skill_id is None:
            _log.warning(
                "Skill '%s' not resolved for cert %s — skipping",
                discovered.skill_name, cert_id,
            )
            continue

        db.add(CertificationSkill(
            certification_id=cert_id,
            skill_id=skill_id,
            weight=discovered.weight,
            certification_domain_id=discovered.primary_domain_id,
            source="agent_discovered",
        ))

    await db.flush()

    _log.info(
        "persist_cert_skill_mapping cert=%s skills_created=%d skills_matched=%d confidence=%s",
        cert_id, skills_created, skills_matched, output.confidence,
    )

    return {
        "skills_created": skills_created,
        "skills_matched": skills_matched,
        "confidence": output.confidence,
    }
