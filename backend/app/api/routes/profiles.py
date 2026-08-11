"""Practitioner profiles API — Phase 6.1.

Routes:
  POST   /practitioners/{id}/profiles
  GET    /practitioners/{id}/profiles
  GET    /practitioners/{id}/profiles/{profile_id}
  PATCH  /practitioners/{id}/profiles/{profile_id}
  PATCH  /practitioners/{id}/profiles/{profile_id}/activate
  POST   /practitioners/{id}/profiles/{profile_id}/skill-assessments
  DELETE /practitioners/{id}/profiles/{profile_id}
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps.session import (
    SessionInfo,
    enforce_self_or_admin,
    require_any_authenticated,
)
from app.db.models import (
    Certification,
    CertificationSkill,
    PractitionerProfile,
    ProfileSkillAssessment,
    SkillProfileSnapshot,
)
from app.db.session import get_db
from app.schemas.profiles import (
    ProfileCreate,
    ProfileDetail,
    ProfileRead,
    ProfileUpdate,
    SkillAssessmentUpsertRequest,
    SkillAssessmentUpsertResponse,
)

router = APIRouter(tags=["profiles"])


def _profile_read(
    profile: PractitionerProfile,
    cert_code: str | None,
    mastery_pct: float | None,
) -> ProfileRead:
    return ProfileRead(
        id=profile.id,
        practitioner_id=profile.practitioner_id,
        name=profile.name,
        is_active=profile.is_active,
        certification_id=profile.certification_id,
        certification_code=cert_code,
        questionnaire_snapshot=profile.questionnaire_snapshot,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        mastery_pct=mastery_pct,
        is_locked=profile.is_locked,
    )


async def _compute_mastery_pct(
    db: AsyncSession,
    practitioner_id: str,
    certification_id: str | None,
) -> float | None:
    """Compute mean mastery of certification's skills from snapshots. None if no cert."""
    if certification_id is None:
        return None

    # Get cert's skill IDs
    cert_skills_result = await db.execute(
        select(CertificationSkill.skill_id).where(
            CertificationSkill.certification_id == certification_id
        )
    )
    skill_ids = [row[0] for row in cert_skills_result.all()]
    if not skill_ids:
        return None

    # Get mastery scores for those skills
    snapshots_result = await db.execute(
        select(SkillProfileSnapshot.mastery_score).where(
            SkillProfileSnapshot.practitioner_id == practitioner_id,
            SkillProfileSnapshot.skill_id.in_(skill_ids),
        )
    )
    scores = [float(row[0]) for row in snapshots_result.all()]
    if not scores:
        return None

    return sum(scores) / len(scores)


@router.post(
    "/practitioners/{practitioner_id}/profiles",
    response_model=ProfileRead,
    status_code=201,
)
async def create_profile(
    practitioner_id: str,
    body: ProfileCreate,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> ProfileRead:
    enforce_self_or_admin(session, practitioner_id)

    profile = PractitionerProfile(
        id=str(uuid.uuid4()),
        practitioner_id=practitioner_id,
        name=body.name,
        is_active=False,
        certification_id=body.certification_id,
        questionnaire_snapshot=body.questionnaire_snapshot,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)

    cert_code: str | None = None
    if profile.certification_id:
        cert = await db.get(Certification, profile.certification_id)
        cert_code = cert.code if cert else None

    mastery_pct = await _compute_mastery_pct(db, practitioner_id, profile.certification_id)
    return _profile_read(profile, cert_code, mastery_pct)


@router.get(
    "/practitioners/{practitioner_id}/profiles",
    response_model=list[ProfileRead],
)
async def list_profiles(
    practitioner_id: str,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> list[ProfileRead]:
    enforce_self_or_admin(session, practitioner_id)

    result = await db.execute(
        select(PractitionerProfile)
        .where(PractitionerProfile.practitioner_id == practitioner_id)
        .order_by(PractitionerProfile.created_at.desc())
    )
    profiles = result.scalars().all()

    out: list[ProfileRead] = []
    for p in profiles:
        cert_code: str | None = None
        if p.certification_id:
            cert = await db.get(Certification, p.certification_id)
            cert_code = cert.code if cert else None
        mastery_pct = await _compute_mastery_pct(db, practitioner_id, p.certification_id)
        out.append(_profile_read(p, cert_code, mastery_pct))

    return out


@router.get(
    "/practitioners/{practitioner_id}/profiles/{profile_id}",
    response_model=ProfileDetail,
)
async def get_profile(
    practitioner_id: str,
    profile_id: str,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> ProfileDetail:
    enforce_self_or_admin(session, practitioner_id)

    result = await db.execute(
        select(PractitionerProfile)
        .options(selectinload(PractitionerProfile.skill_assessments))
        .where(
            PractitionerProfile.id == profile_id,
            PractitionerProfile.practitioner_id == practitioner_id,
        )
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    cert_code: str | None = None
    if profile.certification_id:
        cert = await db.get(Certification, profile.certification_id)
        cert_code = cert.code if cert else None

    mastery_pct = await _compute_mastery_pct(db, practitioner_id, profile.certification_id)

    return ProfileDetail(
        id=profile.id,
        practitioner_id=profile.practitioner_id,
        name=profile.name,
        is_active=profile.is_active,
        certification_id=profile.certification_id,
        certification_code=cert_code,
        questionnaire_snapshot=profile.questionnaire_snapshot,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        mastery_pct=mastery_pct,
        is_locked=profile.is_locked,
        skill_assessments=[
            {
                "id": sa.id,
                "profile_id": sa.profile_id,
                "skill_id": sa.skill_id,
                "signal_strength": float(sa.signal_strength),
                "updated_at": sa.updated_at,
            }
            for sa in profile.skill_assessments
        ],
    )


@router.patch(
    "/practitioners/{practitioner_id}/profiles/{profile_id}",
    response_model=ProfileRead,
)
async def update_profile(
    practitioner_id: str,
    profile_id: str,
    body: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> ProfileRead:
    enforce_self_or_admin(session, practitioner_id)

    profile = await db.get(PractitionerProfile, profile_id)
    if profile is None or profile.practitioner_id != practitioner_id:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Phase 9.3: locked profiles are immutable — create a new profile to make changes.
    if profile.is_locked:
        raise HTTPException(
            status_code=403,
            detail="Profile is locked and cannot be edited. Create a new profile to make changes.",
        )

    if body.name is not None:
        profile.name = body.name
    if body.certification_id is not None:
        profile.certification_id = body.certification_id
    if body.questionnaire_snapshot is not None:
        profile.questionnaire_snapshot = body.questionnaire_snapshot
    profile.updated_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(profile)

    cert_code: str | None = None
    if profile.certification_id:
        cert = await db.get(Certification, profile.certification_id)
        cert_code = cert.code if cert else None

    mastery_pct = await _compute_mastery_pct(db, practitioner_id, profile.certification_id)
    return _profile_read(profile, cert_code, mastery_pct)


@router.patch(
    "/practitioners/{practitioner_id}/profiles/{profile_id}/activate",
    response_model=ProfileRead,
)
async def activate_profile(
    practitioner_id: str,
    profile_id: str,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> ProfileRead:
    """Atomically set is_active=True on this profile and False on all others."""
    enforce_self_or_admin(session, practitioner_id)

    profile = await db.get(PractitionerProfile, profile_id)
    if profile is None or profile.practitioner_id != practitioner_id:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Deactivate all others first
    await db.execute(
        update(PractitionerProfile)
        .where(
            PractitionerProfile.practitioner_id == practitioner_id,
            PractitionerProfile.id != profile_id,
        )
        .values(is_active=False, updated_at=datetime.now(UTC))
    )

    profile.is_active = True
    profile.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(profile)

    cert_code: str | None = None
    if profile.certification_id:
        cert = await db.get(Certification, profile.certification_id)
        cert_code = cert.code if cert else None

    mastery_pct = await _compute_mastery_pct(db, practitioner_id, profile.certification_id)
    return _profile_read(profile, cert_code, mastery_pct)


@router.post(
    "/practitioners/{practitioner_id}/profiles/{profile_id}/skill-assessments",
    response_model=SkillAssessmentUpsertResponse,
)
async def upsert_skill_assessments(
    practitioner_id: str,
    profile_id: str,
    body: SkillAssessmentUpsertRequest,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> SkillAssessmentUpsertResponse:
    """Upsert skill ratings for a profile. One row per skill, unique on (profile_id, skill_id)."""
    enforce_self_or_admin(session, practitioner_id)

    profile = await db.get(PractitionerProfile, profile_id)
    if profile is None or profile.practitioner_id != practitioner_id:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Phase 9.3: locked profiles cannot be re-rated.
    if profile.is_locked:
        raise HTTPException(
            status_code=403,
            detail="Profile is locked and cannot be edited. Create a new profile to make changes.",
        )

    now = datetime.now(UTC)
    rows_written = 0

    for rating in body.assessments:
        existing_result = await db.execute(
            select(ProfileSkillAssessment).where(
                ProfileSkillAssessment.profile_id == profile_id,
                ProfileSkillAssessment.skill_id == rating.skill_id,
            )
        )
        existing = existing_result.scalar_one_or_none()

        if existing is not None:
            existing.signal_strength = rating.signal_strength
            existing.updated_at = now
        else:
            db.add(
                ProfileSkillAssessment(
                    id=str(uuid.uuid4()),
                    profile_id=profile_id,
                    skill_id=rating.skill_id,
                    signal_strength=rating.signal_strength,
                    updated_at=now,
                )
            )
        rows_written += 1

    # Auto-activate if no active profile exists for this practitioner
    active_result = await db.execute(
        select(PractitionerProfile).where(
            PractitionerProfile.practitioner_id == practitioner_id,
            PractitionerProfile.is_active.is_(True),
        )
    )
    active_profile = active_result.scalar_one_or_none()
    if active_profile is None:
        await db.execute(
            update(PractitionerProfile)
            .where(PractitionerProfile.id == profile_id)
            .values(is_active=True, updated_at=now)
        )

    # Phase 9.3: saving skill ratings is the "done" moment — lock the profile
    # in the same transaction so the lock and the rows are always consistent.
    await db.execute(
        update(PractitionerProfile)
        .where(PractitionerProfile.id == profile_id)
        .values(is_locked=True, updated_at=now)
    )

    await db.commit()
    return SkillAssessmentUpsertResponse(rows_written=rows_written)


@router.delete(
    "/practitioners/{practitioner_id}/profiles/{profile_id}",
    status_code=204,
)
async def delete_profile(
    practitioner_id: str,
    profile_id: str,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> FastAPIResponse:
    enforce_self_or_admin(session, practitioner_id)

    profile = await db.get(PractitionerProfile, profile_id)
    if profile is None or profile.practitioner_id != practitioner_id:
        raise HTTPException(status_code=404, detail="Profile not found")

    if profile.is_active:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete the active profile. Activate another profile first.",
        )

    await db.delete(profile)
    await db.commit()
    return FastAPIResponse(status_code=204)
