"""Practitioners API — CRUD + skill profile read.

Step 2.1 scenarios:
  - Creating then fetching a practitioner returns matching data.
  - Fetching a nonexistent practitioner returns 404, not a 500.

Step 5.2 — Auth applied:
  - GET  /practitioners               → require_admin (list all practitioners)
  - POST /practitioners               → require_admin (admin creates; login creates practitioners)
  - GET  /practitioners/{id}          → require_any_authenticated + self-enforcement
  - PATCH /practitioners/{id}         → require_any_authenticated + self-enforcement
  - GET  /practitioners/{id}/skill-profile → require_any_authenticated + self-enforcement
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.session import (
    SessionInfo,
    enforce_self_or_admin,
    require_admin,
    require_any_authenticated,
)
from app.db.models import Practitioner, Skill, SkillProfileEvent, SkillProfileSnapshot, PractitionerProfile, CertificationSkill, CertificationDomain
from app.db.session import get_db
from app.schemas.practitioners import (
    PractitionerCreate,
    PractitionerRead,
    PractitionerUpdate,
    SelfAssessmentRequest,
    SelfAssessmentResponse,
    SkillSnapshotRead,
)

router = APIRouter(prefix="/practitioners", tags=["practitioners"])


@router.post("", response_model=PractitionerRead, status_code=201)
async def create_practitioner(
    body: PractitionerCreate,
    db: AsyncSession = Depends(get_db),
    _session: SessionInfo = Depends(require_admin),
) -> PractitionerRead:
    """Create a new practitioner. Admin only — normal practitioners are created via login."""
    practitioner = Practitioner(
        id=str(uuid.uuid4()),
        name=body.name,
        email=body.email,
        role=body.role,
        practice=body.practice,
        seniority_level=body.seniority_level,
    )
    db.add(practitioner)
    await db.commit()
    await db.refresh(practitioner)
    return PractitionerRead.model_validate(practitioner)


@router.get("", response_model=list[PractitionerRead])
async def list_practitioners(
    db: AsyncSession = Depends(get_db),
    _session: SessionInfo = Depends(require_admin),
) -> list[PractitionerRead]:
    """List all practitioners. Admin only."""
    result = await db.execute(select(Practitioner).order_by(Practitioner.name))
    practitioners = result.scalars().all()
    return [PractitionerRead.model_validate(p) for p in practitioners]


@router.get("/{practitioner_id}", response_model=PractitionerRead)
async def get_practitioner(
    practitioner_id: str,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> PractitionerRead:
    """Fetch one practitioner. Practitioner sees own data; full admin sees all."""
    enforce_self_or_admin(session, practitioner_id)
    practitioner = await db.get(Practitioner, practitioner_id)
    if practitioner is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")
    return PractitionerRead.model_validate(practitioner)


@router.patch("/{practitioner_id}", response_model=PractitionerRead)
async def update_practitioner(
    practitioner_id: str,
    body: PractitionerUpdate,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> PractitionerRead:
    """Partial update of practitioner fields. Practitioner edits own; admin edits any."""
    enforce_self_or_admin(session, practitioner_id)
    practitioner = await db.get(Practitioner, practitioner_id)
    if practitioner is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(practitioner, field, value)
    await db.commit()
    await db.refresh(practitioner)
    return PractitionerRead.model_validate(practitioner)


@router.post(
    "/{practitioner_id}/self-assessment",
    response_model=SelfAssessmentResponse,
    status_code=201,
)
async def submit_self_assessment(
    practitioner_id: str,
    body: SelfAssessmentRequest,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> SelfAssessmentResponse:
    """Record a practitioner's self-assessed skill levels.

    Each assessment item writes one skill_profile_event with source='self_assessment'.
    These events are read by the Skill Profiler the next time a learning path is
    generated, updating the mastery scores and the Skill Radar.

    Skips any skill_id not present in the skills catalog (avoids FK violations if
    the client sends a stale ID).
    """
    enforce_self_or_admin(session, practitioner_id)
    practitioner = await db.get(Practitioner, practitioner_id)
    if practitioner is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")

    # Build a set of valid skill IDs to guard against stale client data
    valid_skills_result = await db.execute(select(Skill.id))
    valid_skill_ids: set[str] = {row[0] for row in valid_skills_result.all()}

    now = datetime.now(UTC)
    written = 0
    for item in body.assessments:
        if item.skill_id not in valid_skill_ids:
            continue  # silently skip unknown skills
        db.add(SkillProfileEvent(
            id=str(uuid.uuid4()),
            practitioner_id=practitioner_id,
            skill_id=item.skill_id,
            source="self_assessment",
            signal_strength=item.signal_strength,
            occurred_at=now,
            metadata_=None,
        ))
        written += 1

    await db.commit()
    return SelfAssessmentResponse(events_written=written)


@router.get("/{practitioner_id}/skill-profile", response_model=list[SkillSnapshotRead])
async def get_skill_profile(
    practitioner_id: str,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> list[SkillSnapshotRead]:
    """Return a practitioner's current skill profile with optional domain enrichment.

    Phase 13.4: when the practitioner's active profile has a certification with
    agent-discovered skills, each snapshot is enriched with its domain name and
    weight for color-coded radar display.
    """
    enforce_self_or_admin(session, practitioner_id)
    practitioner = await db.get(Practitioner, practitioner_id)
    if practitioner is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")

    # Fetch snapshots + skill names
    result = await db.execute(
        select(SkillProfileSnapshot, Skill)
        .join(Skill, Skill.id == SkillProfileSnapshot.skill_id)
        .where(SkillProfileSnapshot.practitioner_id == practitioner_id)
        .order_by(SkillProfileSnapshot.mastery_score.desc())
    )
    rows = result.all()

    # Phase 13.4: build domain lookup from agent_discovered cert skills.
    # skill_id → (domain_id, domain_name, domain_weight_pct)
    domain_by_skill: dict[str, tuple[str, str, float]] = {}

    active_profile_result = await db.execute(
        select(PractitionerProfile).where(
            PractitionerProfile.practitioner_id == practitioner_id,
            PractitionerProfile.is_active == True,  # noqa: E712
        )
    )
    active_profile = active_profile_result.scalar_one_or_none()

    if active_profile is not None and active_profile.certification_id is not None:
        # Prefer agent_discovered; fall back to seed if none
        ad_result = await db.execute(
            select(CertificationSkill).where(
                CertificationSkill.certification_id == active_profile.certification_id,
                CertificationSkill.source == "agent_discovered",
                CertificationSkill.certification_domain_id != None,  # noqa: E711
            )
        )
        cert_skills = ad_result.scalars().all()

        if not cert_skills:
            # Fallback to seed rows that have a domain link
            seed_result = await db.execute(
                select(CertificationSkill).where(
                    CertificationSkill.certification_id == active_profile.certification_id,
                    CertificationSkill.certification_domain_id != None,  # noqa: E711
                )
            )
            cert_skills = seed_result.scalars().all()

        for cs in cert_skills:
            if cs.certification_domain_id:
                domain = await db.get(CertificationDomain, cs.certification_domain_id)
                if domain:
                    domain_by_skill[cs.skill_id] = (
                        domain.id,
                        domain.domain_name,
                        float(domain.weight_pct),
                    )

    # Build response
    out: list[SkillSnapshotRead] = []
    for snap, skill in rows:
        domain_info = domain_by_skill.get(snap.skill_id)
        out.append(SkillSnapshotRead(
            skill_id=snap.skill_id,
            skill_name=skill.name,
            mastery_score=float(snap.mastery_score),
            confidence=float(snap.confidence),
            last_computed_at=snap.last_computed_at,
            certification_domain_id=domain_info[0] if domain_info else None,
            certification_domain_name=domain_info[1] if domain_info else None,
            domain_weight_pct=domain_info[2] if domain_info else None,
        ))

    return out
