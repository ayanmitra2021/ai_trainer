"""Practitioners API — CRUD + skill profile read.

Step 2.1 scenarios:
  - Creating then fetching a practitioner returns matching data.
  - Fetching a nonexistent practitioner returns 404, not a 500.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Practitioner, SkillProfileSnapshot, Skill
from app.db.session import get_db
from app.schemas.practitioners import (
    PractitionerCreate,
    PractitionerRead,
    PractitionerUpdate,
    SkillSnapshotRead,
)

router = APIRouter(prefix="/practitioners", tags=["practitioners"])


@router.post("", response_model=PractitionerRead, status_code=201)
async def create_practitioner(
    body: PractitionerCreate, db: AsyncSession = Depends(get_db)
) -> PractitionerRead:
    """Create a new practitioner."""
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
async def list_practitioners(db: AsyncSession = Depends(get_db)) -> list[PractitionerRead]:
    """List all practitioners."""
    result = await db.execute(select(Practitioner).order_by(Practitioner.name))
    practitioners = result.scalars().all()
    return [PractitionerRead.model_validate(p) for p in practitioners]


@router.get("/{practitioner_id}", response_model=PractitionerRead)
async def get_practitioner(
    practitioner_id: str, db: AsyncSession = Depends(get_db)
) -> PractitionerRead:
    """Fetch one practitioner by ID."""
    practitioner = await db.get(Practitioner, practitioner_id)
    if practitioner is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")
    return PractitionerRead.model_validate(practitioner)


@router.patch("/{practitioner_id}", response_model=PractitionerRead)
async def update_practitioner(
    practitioner_id: str,
    body: PractitionerUpdate,
    db: AsyncSession = Depends(get_db),
) -> PractitionerRead:
    """Partial update of practitioner fields."""
    practitioner = await db.get(Practitioner, practitioner_id)
    if practitioner is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(practitioner, field, value)
    await db.commit()
    await db.refresh(practitioner)
    return PractitionerRead.model_validate(practitioner)


@router.get("/{practitioner_id}/skill-profile", response_model=list[SkillSnapshotRead])
async def get_skill_profile(
    practitioner_id: str, db: AsyncSession = Depends(get_db)
) -> list[SkillSnapshotRead]:
    """Return a practitioner's current skill profile (all snapshots)."""
    practitioner = await db.get(Practitioner, practitioner_id)
    if practitioner is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")

    result = await db.execute(
        select(SkillProfileSnapshot, Skill)
        .join(Skill, Skill.id == SkillProfileSnapshot.skill_id)
        .where(SkillProfileSnapshot.practitioner_id == practitioner_id)
        .order_by(SkillProfileSnapshot.mastery_score.desc())
    )
    rows = result.all()
    return [
        SkillSnapshotRead(
            skill_id=snap.skill_id,
            skill_name=skill.name,
            mastery_score=float(snap.mastery_score),
            confidence=float(snap.confidence),
            last_computed_at=snap.last_computed_at,
        )
        for snap, skill in rows
    ]
