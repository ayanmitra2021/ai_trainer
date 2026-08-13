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

import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

from app.api.deps.session import (
    SessionInfo,
    enforce_self_or_admin,
    require_any_authenticated,
)
from app.db.models import (
    Certification,
    CertificationDomain,
    CertificationDomainScore,
    CertificationDomainVersion,
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


# ── Phase 14.3: mechanical domain scoring fallback ───────────────────────────


async def _compute_degraded_domain_scores(
    profile: PractitionerProfile,
    cert_domains: list[CertificationDomain],
    skill_assessments: list,  # list of ProfileSkillAssessment ORM rows
    db: AsyncSession,
    now: datetime,
) -> None:
    """Write degraded domain score estimates when the Domain Scorer LLM is unavailable.

    For each certification domain:
    1. Collect signal_strength values from profile_skill_assessments whose skills
       are linked to that domain via certification_skills (agent_discovered or seed).
    2. Cap the average at 0.5 (same ceiling as LLM-derived estimates).
    3. Write CertificationDomainScore rows with source='degraded_estimate',
       confidence=0.3, overwriting any existing non-quiz_derived rows.

    domain-agnostic fallback: if no skills are linked to a domain, fall back to
    the mean of all assessments.
    """
    practitioner_id = profile.practitioner_id

    # Build a map of skill_id → signal_strength from the assessments
    skill_strength: dict[str, float] = {
        sa_row.skill_id: float(sa_row.signal_strength)
        for sa_row in skill_assessments
    }

    # Build a map of domain_id → list of skill_ids (from certification_skills)
    domain_skill_ids: dict[str, list[str]] = {}
    for domain in cert_domains:
        result = await db.execute(
            select(CertificationSkill.skill_id).where(
                CertificationSkill.certification_id == profile.certification_id,
                CertificationSkill.certification_domain_id == domain.id,
            )
        )
        domain_skill_ids[domain.id] = [row[0] for row in result.all()]

    # Fallback: all skill strengths (for domains with no linked skills)
    all_strengths = list(skill_strength.values())
    global_avg = (sum(all_strengths) / len(all_strengths)) if all_strengths else 0.0
    global_avg = min(global_avg, 0.5)

    for domain in cert_domains:
        linked_ids = domain_skill_ids.get(domain.id, [])
        if linked_ids:
            strengths = [skill_strength[sid] for sid in linked_ids if sid in skill_strength]
            avg_score = (sum(strengths) / len(strengths)) if strengths else global_avg
        else:
            avg_score = global_avg

        avg_score = min(avg_score, 0.5)  # cap at 0.5

        # Upsert — never overwrite quiz_derived rows
        existing_result = await db.execute(
            select(CertificationDomainScore).where(
                CertificationDomainScore.practitioner_id == practitioner_id,
                CertificationDomainScore.certification_domain_id == domain.id,
            )
        )
        existing = existing_result.scalar_one_or_none()

        if existing is None:
            db.add(CertificationDomainScore(
                id=str(uuid.uuid4()),
                practitioner_id=practitioner_id,
                certification_domain_id=domain.id,
                mastery_score=avg_score,
                confidence=0.3,
                source="degraded_estimate",
                last_computed_at=now,
            ))
        elif existing.source != "quiz_derived":
            existing.mastery_score = avg_score
            existing.confidence = 0.3
            existing.source = "degraded_estimate"
            existing.last_computed_at = now


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
        domain_scoring_status=getattr(profile, "domain_scoring_status", "pending"),
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
        domain_scoring_status=getattr(profile, "domain_scoring_status", "pending"),
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
    await db.flush()

    # Phase 10.5: freeze the current domain version on the profile and run the
    # Domain Scorer agent to create initial certification_domain_scores.
    await db.refresh(profile)
    if profile.certification_id is not None:
        # Find the current domain version for this cert
        version_result = await db.execute(
            select(CertificationDomainVersion).where(
                CertificationDomainVersion.certification_id == profile.certification_id,
                CertificationDomainVersion.is_current == True,  # noqa: E712
            )
        )
        current_version = version_result.scalar_one_or_none()

        if current_version is not None:
            # Freeze the domain version on the profile
            await db.execute(
                update(PractitionerProfile)
                .where(PractitionerProfile.id == profile_id)
                .values(domain_version_id=current_version.id)
            )
            await db.flush()

            # Get certification domains for this version
            domains_result = await db.execute(
                select(CertificationDomain).where(
                    CertificationDomain.certification_id == profile.certification_id,
                    CertificationDomain.domain_version_id == current_version.id,
                ).order_by(CertificationDomain.sequence_order)
            )
            cert_domains = domains_result.scalars().all()

            if cert_domains:
                # Build skill assessments list for the Domain Scorer
                assessments_result = await db.execute(
                    select(ProfileSkillAssessment).where(
                        ProfileSkillAssessment.profile_id == profile_id
                    )
                )
                assessments = assessments_result.scalars().all()

                # Load skill names for each assessment
                from app.db.models import Skill
                skill_assessments_data: list[dict] = []
                for sa_row in assessments:
                    skill = await db.get(Skill, sa_row.skill_id)
                    skill_assessments_data.append({
                        "skill_name": skill.name if skill else sa_row.skill_id,
                        "signal_strength": float(sa_row.signal_strength),
                    })

                # Run the Domain Scorer agent — Phase 15: catch AllProvidersUnavailableError
                from app.agents.domain_scorer import DomainScorerAgent, DomainScorerInput
                from app.agents.model_client import (
                    AllProvidersUnavailableError,
                    ProviderUnavailableError,
                    create_model_client,
                )

                model_client = create_model_client()
                scorer = DomainScorerAgent(client=model_client, db_session=db)

                scorer_input = DomainScorerInput(
                    certification_id=profile.certification_id,
                    certification_domains=[
                        {
                            "id": d.id,
                            "name": d.domain_name,
                            "description": d.domain_description,
                            "weight_pct": float(d.weight_pct),
                        }
                        for d in cert_domains
                    ],
                    skill_assessments=skill_assessments_data,
                )

                try:
                    scorer_output = await scorer.run(scorer_input)

                    # Persist LLM-derived domain scores
                    for domain_score in scorer_output.domain_scores:
                        existing_result = await db.execute(
                            select(CertificationDomainScore).where(
                                CertificationDomainScore.practitioner_id == practitioner_id,
                                CertificationDomainScore.certification_domain_id
                                == domain_score.certification_domain_id,
                            )
                        )
                        existing = existing_result.scalar_one_or_none()

                        if existing is None:
                            # No score yet — create self_assessment_estimate
                            import uuid as _uuid
                            db.add(CertificationDomainScore(
                                id=str(_uuid.uuid4()),
                                practitioner_id=practitioner_id,
                                certification_domain_id=domain_score.certification_domain_id,
                                mastery_score=domain_score.initial_score,
                                confidence=domain_score.confidence,
                                source="self_assessment_estimate",
                                last_computed_at=now,
                            ))
                        elif existing.source != "quiz_derived":
                            # Update existing self_assessment_estimate
                            existing.mastery_score = domain_score.initial_score
                            existing.confidence = domain_score.confidence
                            existing.last_computed_at = now

                        # quiz_derived rows are never overwritten by estimates

                    # Phase 14.3: mark profile as LLM-scored
                    await db.execute(
                        update(PractitionerProfile)
                        .where(PractitionerProfile.id == profile_id)
                        .values(domain_scoring_status="lm_scored")
                    )

                except (AllProvidersUnavailableError, ProviderUnavailableError):
                    # Phase 15: all providers failed — compute mechanical estimates
                    # (Domain Scorer is the only route that degrades gracefully;
                    # other routes let the exception propagate to the 503 handler.)
                    logger.warning(
                        "Domain Scorer unavailable (all providers failed) — "
                        "using mechanical estimate for profile %s",
                        profile_id,
                    )
                    # Re-fetch assessments fresh (already flushed to DB above)
                    assessments_result2 = await db.execute(
                        select(ProfileSkillAssessment).where(
                            ProfileSkillAssessment.profile_id == profile_id
                        )
                    )
                    assessments_fresh = assessments_result2.scalars().all()
                    await _compute_degraded_domain_scores(
                        profile, cert_domains, assessments_fresh, db, now
                    )
                    await db.execute(
                        update(PractitionerProfile)
                        .where(PractitionerProfile.id == profile_id)
                        .values(domain_scoring_status="degraded")
                    )

                await db.flush()

    # Phase 13.3: ensure cert has agent-discovered skills before path generation.
    # If no agent_discovered rows exist for this cert, trigger the mapper now
    # (60 s timeout — timeout does not fail the lock).
    if profile.certification_id is not None:
        import asyncio
        from sqlalchemy import func as sql_func
        from app.agents.cert_skill_mapper import CertSkillMapperAgent, CertSkillMapperInput, CertSkillMapperDomain
        from app.services.cert_skill_mapper_service import persist_cert_skill_mapping

        skill_count_result = await db.execute(
            select(sql_func.count()).select_from(CertificationSkill).where(
                CertificationSkill.certification_id == profile.certification_id,
                CertificationSkill.source == "agent_discovered",
            )
        )
        if skill_count_result.scalar() == 0:
            try:
                async def _run_mapper():
                    _domains_result = await db.execute(
                        select(CertificationDomain).where(
                            CertificationDomain.certification_id == profile.certification_id,
                        ).order_by(CertificationDomain.sequence_order)
                    )
                    _cert_domains = _domains_result.scalars().all()
                    if not _cert_domains:
                        return
                    _cert = await db.get(Certification, profile.certification_id)
                    if _cert is None:
                        return
                    _mapper_input = CertSkillMapperInput(
                        cert_code=_cert.code,
                        cert_name=_cert.name,
                        cert_external_url=_cert.external_url,
                        domains=[
                            CertSkillMapperDomain(
                                domain_id=d.id,
                                domain_name=d.domain_name,
                                domain_description=d.domain_description,
                                weight_pct=float(d.weight_pct),
                            )
                            for d in _cert_domains
                        ],
                    )
                    from app.agents.model_client import create_model_client as _create_mc
                    _mc = _create_mc()
                    _mapper = CertSkillMapperAgent(client=_mc, db_session=db)
                    _output = await _mapper.run(_mapper_input)
                    await persist_cert_skill_mapping(profile.certification_id, "", _output, db)

                import logging as _logging
                _plog = _logging.getLogger(__name__)
                await asyncio.wait_for(_run_mapper(), timeout=60.0)
                _plog.info("CertSkillMapper completed for cert %s at profile lock", profile.certification_id)
            except asyncio.TimeoutError:
                import logging as _log2
                _log2.getLogger(__name__).warning(
                    "CertSkillMapper timed out for cert %s — using seed skills for first path",
                    profile.certification_id,
                )
            except Exception as _exc:
                import logging as _log3
                _log3.getLogger(__name__).warning(
                    "CertSkillMapper failed for cert %s: %s — using seed skills",
                    profile.certification_id, _exc,
                )

    await db.commit()
    # Refresh to pick up domain_scoring_status set by UPDATE statements above
    await db.refresh(profile)
    return SkillAssessmentUpsertResponse(
        rows_written=rows_written,
        domain_scoring_status=getattr(profile, "domain_scoring_status", "pending"),
    )


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

    was_active = profile.is_active

    await db.delete(profile)
    await db.flush()  # remove the row before we query for a replacement

    # If the deleted profile was active, auto-promote the most recent other profile.
    if was_active:
        result = await db.execute(
            select(PractitionerProfile)
            .where(PractitionerProfile.practitioner_id == practitioner_id)
            .order_by(PractitionerProfile.created_at.desc())
            .limit(1)
        )
        next_profile = result.scalar_one_or_none()
        if next_profile is not None:
            next_profile.is_active = True

    await db.commit()
    return FastAPIResponse(status_code=204)
