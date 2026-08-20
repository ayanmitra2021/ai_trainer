"""Plan enforcement — Phase 22.

PlanEnforcer is instantiated per-request with the practitioner's resolved plan.
Call its check_* methods before creating resources — they raise HTTP 402 if the
plan limit is reached.
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    LearningPath,
    MockExamSession,
    Organization,
    Practitioner,
    PractitionerProfile,
    SubscriptionPlan,
)


def _free_plan() -> SubscriptionPlan:
    """Synthetic Free plan used when a practitioner has no org or the org has no plan."""
    return SubscriptionPlan(
        max_profiles_per_practitioner=2,
        max_learning_paths=2,
        max_mock_exams_per_profile=2,
        max_practitioners_per_org=-1,
        allow_cert_recycling=False,
        nudges_enabled=False,
        teams_notifications_enabled=False,
        name="Free",
        tier="free",
    )


class PlanEnforcer:
    """Validates resource creation against plan limits.

    Raises HTTP 402 with structured detail when a limit is reached.
    -1 means unlimited — the check is skipped.
    """

    def __init__(self, plan: SubscriptionPlan) -> None:
        self._plan = plan

    async def check_profile_count(self, db: AsyncSession, practitioner_id: str) -> None:
        """Raise 402 if the practitioner is at their profile limit."""
        if self._plan.max_profiles_per_practitioner == -1:
            return
        result = await db.execute(
            select(func.count()).select_from(PractitionerProfile).where(
                PractitionerProfile.practitioner_id == practitioner_id,
                PractitionerProfile.deleted_at.is_(None),
            )
        )
        count = result.scalar_one()
        if count >= self._plan.max_profiles_per_practitioner:
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "plan_limit_reached",
                    "limit_type": "profiles",
                    "current_count": count,
                    "plan_limit": self._plan.max_profiles_per_practitioner,
                    "plan_name": self._plan.name,
                    "upgrade_message": (
                        f"You have reached the {self._plan.name} plan limit for certification profiles. "
                        "Delete an existing profile or upgrade your plan to create a new one."
                    ),
                },
            )

    async def check_learning_path_count(self, db: AsyncSession, practitioner_id: str) -> None:
        """Raise 402 if the practitioner is at their learning path limit."""
        if self._plan.max_learning_paths == -1:
            return
        result = await db.execute(
            select(func.count()).select_from(LearningPath).where(
                LearningPath.practitioner_id == practitioner_id,
            )
        )
        count = result.scalar_one()
        if count >= self._plan.max_learning_paths:
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "plan_limit_reached",
                    "limit_type": "learning_paths",
                    "current_count": count,
                    "plan_limit": self._plan.max_learning_paths,
                    "plan_name": self._plan.name,
                    "upgrade_message": (
                        f"You have reached the {self._plan.name} plan limit for learning path generations. "
                        "Upgrade your plan to generate more learning paths."
                    ),
                },
            )

    async def check_mock_exam_count(
        self,
        db: AsyncSession,
        practitioner_id: str,
        profile_id: str,
    ) -> None:
        """Raise 402 if the practitioner is at their mock exam limit for this profile's cert."""
        if self._plan.max_mock_exams_per_profile == -1:
            return
        profile = await db.get(PractitionerProfile, profile_id)
        if profile is None:
            return
        result = await db.execute(
            select(func.count()).select_from(MockExamSession).where(
                MockExamSession.practitioner_id == practitioner_id,
                MockExamSession.certification_id == profile.certification_id,
            )
        )
        count = result.scalar_one()
        if count >= self._plan.max_mock_exams_per_profile:
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "plan_limit_reached",
                    "limit_type": "mock_exams",
                    "current_count": count,
                    "plan_limit": self._plan.max_mock_exams_per_profile,
                    "plan_name": self._plan.name,
                    "upgrade_message": (
                        f"You have reached the {self._plan.name} plan limit for mock exams on this profile. "
                        "Upgrade your plan to take more mock exams."
                    ),
                },
            )


async def get_plan_enforcer(
    practitioner_id: str,
    db: AsyncSession,
) -> PlanEnforcer:
    """Fetch the practitioner's plan and return a PlanEnforcer.

    Falls back to a synthetic Free plan when the practitioner has no org or the
    org has no matching plan row.
    """
    practitioner = await db.get(Practitioner, practitioner_id)
    if practitioner is None or practitioner.organization_id is None:
        return PlanEnforcer(_free_plan())

    org = await db.get(Organization, practitioner.organization_id)
    if org is None:
        return PlanEnforcer(_free_plan())

    plan = await db.get(SubscriptionPlan, org.plan_id)
    if plan is None:
        return PlanEnforcer(_free_plan())

    return PlanEnforcer(plan)
