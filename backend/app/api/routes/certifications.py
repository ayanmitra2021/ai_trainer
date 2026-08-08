"""Certifications API — catalog reads and advisor endpoint.

Routes:
  GET  /certifications                       list the catalog
  POST /certification-advisor                run the advisor and persist results
  GET  /practitioners/{id}/certification-goals
  PATCH /practitioners/{id}/certification-goals/{goal_id}

Step 5.2 — Auth applied:
  - GET  /certifications               → require_any_authenticated
  - POST /certification-advisor        → require_any_authenticated + body self-enforcement
  - GET  /practitioners/{id}/cert-goals → require_any_authenticated + self-enforcement
  - PATCH goal                         → require_any_authenticated + self-enforcement
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps.session import (
    SessionInfo,
    enforce_self_or_admin,
    require_any_authenticated,
)
from app.config import settings
from app.db.models import (
    Certification,
    CertificationAdvisorResponse,
    CertificationProvider,
    CertificationSkill,
    Practitioner,
    PractitionerCertificationGoal,
    PractitionerProfile,
)
from app.db.session import get_db
from app.schemas.certifications import (
    AdvisorOutput,
    AdvisorRequest,
    AdvisorResponse,
    CertificationContext,
    CertificationGoalRead,
    CertificationGoalUpdate,
    CertificationRead,
)

router = APIRouter(tags=["certifications"])


# ── Catalog ────────────────────────────────────────────────────────────────────

@router.get("/certifications", response_model=list[CertificationRead])
async def list_certifications(
    db: AsyncSession = Depends(get_db),
    _session: SessionInfo = Depends(require_any_authenticated),
) -> list[CertificationRead]:
    """Return all active certifications with their provider and skill mappings."""
    result = await db.execute(
        select(Certification)
        .options(
            selectinload(Certification.provider),
            selectinload(Certification.certification_skills),
        )
        .where(Certification.is_active.is_(True))
        .order_by(Certification.code)
    )
    certs = result.scalars().all()
    return [CertificationRead.model_validate(c) for c in certs]


# ── Advisor ────────────────────────────────────────────────────────────────────

@router.post("/certification-advisor", response_model=AdvisorResponse, status_code=201)
async def run_certification_advisor(
    body: AdvisorRequest,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> AdvisorResponse:
    """Run the Certification Advisor for a practitioner and persist results."""
    # Self-enforcement: practitioners can only get advice for themselves
    enforce_self_or_admin(session, body.practitioner_id)

    practitioner = await db.get(Practitioner, body.practitioner_id)
    if practitioner is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")

    result = await db.execute(
        select(Certification)
        .options(selectinload(Certification.provider))
        .where(Certification.is_active.is_(True))
    )
    certs = result.scalars().all()
    catalog = [
        CertificationContext(
            code=c.code,
            name=c.name,
            provider_name=c.provider.name,
            level=c.level,
            requires_coding_background=c.requires_coding_background,
            typical_audience=c.typical_audience,
            focus_area=c.focus_area,
            eligibility_notes=c.eligibility_notes,
        )
        for c in certs
    ]

    from app.agents.certification_advisor import CertificationAdvisorAgent
    from app.agents.certification_advisor import CertificationAdvisorInput
    import anthropic as anthropic_lib

    agent_input = CertificationAdvisorInput(
        practitioner_id=body.practitioner_id,
        answers=body.answers,
        catalog=catalog,
    )

    anthropic_client = anthropic_lib.AsyncAnthropic(api_key=settings.anthropic_api_key)
    agent = CertificationAdvisorAgent(client=anthropic_client, db_session=db)
    recommendation: AdvisorOutput = await agent.run(agent_input)

    response_id = str(uuid.uuid4())
    advisor_response = CertificationAdvisorResponse(
        id=response_id,
        practitioner_id=body.practitioner_id,
        responses=body.answers.model_dump(),
    )
    db.add(advisor_response)
    await db.flush()

    cert_result = await db.execute(
        select(Certification).where(
            Certification.code == recommendation.primary_recommendation_code
        )
    )
    recommended_cert = cert_result.scalar_one_or_none()
    if recommended_cert is None:
        raise HTTPException(
            status_code=422,
            detail=f"Agent returned unknown certification code: "
                   f"{recommendation.primary_recommendation_code}",
        )

    # Check if practitioner has an active profile to link the goal
    profile_result = await db.execute(
        select(PractitionerProfile).where(
            PractitionerProfile.practitioner_id == body.practitioner_id,
            PractitionerProfile.is_active.is_(True),
        )
    )
    active_profile = profile_result.scalar_one_or_none()

    goal_id = str(uuid.uuid4())
    goal = PractitionerCertificationGoal(
        id=goal_id,
        practitioner_id=body.practitioner_id,
        certification_id=recommended_cert.id,
        status="recommended",
        recommended_at=datetime.now(UTC),
        profile_id=active_profile.id if active_profile else None,
    )
    db.add(goal)
    await db.commit()

    return AdvisorResponse(
        practitioner_id=body.practitioner_id,
        advisor_response_id=response_id,
        goal_id=goal_id,
        recommendation=recommendation,
    )


# ── Certification goals ────────────────────────────────────────────────────────

@router.get(
    "/practitioners/{practitioner_id}/certification-goals",
    response_model=list[CertificationGoalRead],
)
async def list_certification_goals(
    practitioner_id: str,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> list[CertificationGoalRead]:
    """Return all certification goals for a practitioner, newest first."""
    enforce_self_or_admin(session, practitioner_id)
    practitioner = await db.get(Practitioner, practitioner_id)
    if practitioner is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")

    result = await db.execute(
        select(PractitionerCertificationGoal, Certification)
        .join(Certification, Certification.id == PractitionerCertificationGoal.certification_id)
        .where(PractitionerCertificationGoal.practitioner_id == practitioner_id)
        .order_by(PractitionerCertificationGoal.recommended_at.desc())
    )
    rows = result.all()
    return [
        CertificationGoalRead(
            id=goal.id,
            practitioner_id=goal.practitioner_id,
            certification_id=goal.certification_id,
            certification_code=cert.code,
            status=goal.status,
            recommended_at=goal.recommended_at,
            selected_at=goal.selected_at,
            achieved_at=goal.achieved_at,
        )
        for goal, cert in rows
    ]


@router.patch(
    "/practitioners/{practitioner_id}/certification-goals/{goal_id}",
    response_model=CertificationGoalRead,
)
async def update_certification_goal(
    practitioner_id: str,
    goal_id: str,
    body: CertificationGoalUpdate,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_any_authenticated),
) -> CertificationGoalRead:
    """Update a certification goal's status (e.g. recommended → selected)."""
    enforce_self_or_admin(session, practitioner_id)
    goal = await db.get(PractitionerCertificationGoal, goal_id)
    if goal is None or goal.practitioner_id != practitioner_id:
        raise HTTPException(status_code=404, detail="Goal not found")

    valid_statuses = {"selected", "in_progress", "achieved", "abandoned"}
    if body.status not in valid_statuses:
        raise HTTPException(
            status_code=422,
            detail=f"status must be one of: {', '.join(sorted(valid_statuses))}",
        )

    goal.status = body.status
    now = datetime.now(UTC)
    if body.status == "selected" and goal.selected_at is None:
        goal.selected_at = now
    if body.status == "achieved" and goal.achieved_at is None:
        goal.achieved_at = now
    await db.commit()
    await db.refresh(goal)

    cert = await db.get(Certification, goal.certification_id)
    return CertificationGoalRead(
        id=goal.id,
        practitioner_id=goal.practitioner_id,
        certification_id=goal.certification_id,
        certification_code=cert.code if cert else "",
        status=goal.status,
        recommended_at=goal.recommended_at,
        selected_at=goal.selected_at,
        achieved_at=goal.achieved_at,
    )
