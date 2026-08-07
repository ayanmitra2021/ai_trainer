"""Recipient resolver for nudge campaigns — Step 7.2.

Pure Python function: translates criteria dict keys into DB queries.
No LLM involved — privacy-preserving by design.

Supported criteria keys:
  no_quiz_days_gte: N          — no attempts in last N days
  no_profile: true             — no active profile
  profile_unrated: true        — active profile but no skill assessments
  mastery_stalled_days_gte: N  — no mastery improvement in last N days
  skill_gap_skill_id: UUID     — gap_score >= 0.5 on this skill
  near_cert_ready: true        — cert-relevant mastery avg >= 80%
  custom_description: str      — free text → returns all practitioners
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Attempt,
    CorrelationSnapshot,
    MasteryHistory,
    Practitioner,
    PractitionerProfile,
    ProfileSkillAssessment,
    SkillProfileSnapshot,
)


async def resolve_recipients(
    criteria: dict[str, Any],
    db: AsyncSession,
) -> list[Practitioner]:
    """Resolve criteria dict to a list of matching Practitioner rows."""

    # custom_description → return everyone (manual review)
    if "custom_description" in criteria:
        result = await db.execute(select(Practitioner).order_by(Practitioner.name))
        return list(result.scalars().all())

    # Start with all practitioners
    all_result = await db.execute(select(Practitioner).order_by(Practitioner.name))
    all_practitioners = list(all_result.scalars().all())
    all_ids = {p.id for p in all_practitioners}
    id_map = {p.id: p for p in all_practitioners}
    candidate_ids = set(all_ids)

    now = datetime.now(UTC)

    # no_quiz_days_gte: N — no attempts in last N days
    if "no_quiz_days_gte" in criteria:
        n = int(criteria["no_quiz_days_gte"])
        cutoff = now - timedelta(days=n)
        active_result = await db.execute(
            select(Attempt.practitioner_id)
            .where(Attempt.attempted_at >= cutoff)
            .distinct()
        )
        active_ids = {row[0] for row in active_result}
        candidate_ids &= all_ids - active_ids

    # no_profile: true — no active profile
    if criteria.get("no_profile") is True or criteria.get("no_profile") == "true":
        with_profile_result = await db.execute(
            select(PractitionerProfile.practitioner_id)
            .where(PractitionerProfile.is_active.is_(True))
            .distinct()
        )
        with_profile_ids = {row[0] for row in with_profile_result}
        candidate_ids &= all_ids - with_profile_ids

    # profile_unrated: true — active profile but no skill assessments
    if criteria.get("profile_unrated") is True or criteria.get("profile_unrated") == "true":
        profile_with_ratings_result = await db.execute(
            select(PractitionerProfile.practitioner_id)
            .join(ProfileSkillAssessment, ProfileSkillAssessment.profile_id == PractitionerProfile.id)
            .where(PractitionerProfile.is_active.is_(True))
            .distinct()
        )
        rated_ids = {row[0] for row in profile_with_ratings_result}
        active_profile_result = await db.execute(
            select(PractitionerProfile.practitioner_id)
            .where(PractitionerProfile.is_active.is_(True))
            .distinct()
        )
        active_profile_ids = {row[0] for row in active_profile_result}
        unrated_ids = active_profile_ids - rated_ids
        candidate_ids &= unrated_ids

    # mastery_stalled_days_gte: N — no mastery improvement in last N days
    if "mastery_stalled_days_gte" in criteria:
        n = int(criteria["mastery_stalled_days_gte"])
        cutoff = now - timedelta(days=n)
        improved_result = await db.execute(
            select(MasteryHistory.practitioner_id)
            .where(MasteryHistory.recorded_at >= cutoff)
            .distinct()
        )
        improved_ids = {row[0] for row in improved_result}
        # "stalled" = has at least one mastery history entry but none recently
        any_history_result = await db.execute(
            select(MasteryHistory.practitioner_id).distinct()
        )
        any_history_ids = {row[0] for row in any_history_result}
        stalled_ids = any_history_ids - improved_ids
        candidate_ids &= stalled_ids

    # skill_gap_skill_id: UUID — gap_score >= 0.5 on this skill
    if "skill_gap_skill_id" in criteria:
        skill_id = criteria["skill_gap_skill_id"]
        gap_result = await db.execute(
            select(CorrelationSnapshot.practitioner_id)
            .where(
                CorrelationSnapshot.skill_id == skill_id,
                CorrelationSnapshot.gap_score >= 0.5,
            )
            .distinct()
        )
        gap_ids = {row[0] for row in gap_result}
        candidate_ids &= gap_ids

    # near_cert_ready: true — cert-relevant mastery avg >= 80%
    if criteria.get("near_cert_ready") is True or criteria.get("near_cert_ready") == "true":
        avg_result = await db.execute(
            select(
                SkillProfileSnapshot.practitioner_id,
                func.avg(SkillProfileSnapshot.mastery_score).label("avg"),
            )
            .group_by(SkillProfileSnapshot.practitioner_id)
            .having(func.avg(SkillProfileSnapshot.mastery_score) >= 0.8)
        )
        ready_ids = {row.practitioner_id for row in avg_result}
        candidate_ids &= ready_ids

    return [id_map[pid] for pid in candidate_ids if pid in id_map]
