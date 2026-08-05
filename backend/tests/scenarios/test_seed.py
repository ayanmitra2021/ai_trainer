"""
Scenario tests — Step 0.3: Synthetic seed data generator.

These are integration tests that require a running Postgres database.
Run with:
    py -m pytest -m integration tests/scenarios/test_seed.py

Scenarios
---------
1. Seeding is idempotent
   Given an already-seeded database,
   When the seed script runs again,
   Then the practitioner count doesn't double.

2. Seeded data spans all signal sources
   Given a freshly seeded database,
   When querying skill_profile_events by source,
   Then 'certification', 'self_assessment', 'quiz_attempt', and
   'project_history' are all represented.
"""

from __future__ import annotations

import os

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.db.models import Practitioner, SkillProfileEvent
from seed.generate import seed, SEED_EMAIL_DOMAIN, PRACTITIONER_NAMES


# ── Helpers ───────────────────────────────────────────────────────────────────

def _session_factory(engine: AsyncEngine) -> async_sessionmaker:
    """Committed session factory — seed() needs to commit, unlike pg_session which rolls back."""
    return async_sessionmaker(engine, expire_on_commit=False)


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestSeedIdempotency:
    async def test_second_seed_does_not_double_practitioners(self, pg_engine: AsyncEngine):
        """
        Scenario: Seeding is idempotent
          Given an already-seeded database (tables created by pg_engine fixture)
          When the seed script runs again
          Then the practitioner count doesn't double

        We accept pg_engine as a fixture parameter to ensure Base.metadata.create_all
        has run before we try to seed — the fixture is session-scoped so this is cheap.
        """
        factory = _session_factory(pg_engine)

        # First seed
        async with factory() as s:
            await seed(s)

        # Count after first seed
        async with factory() as s:
            count_1 = (
                await s.execute(
                    select(func.count()).where(
                        Practitioner.email.like(f"%@{SEED_EMAIL_DOMAIN}")
                    )
                )
            ).scalar_one()

        # Second seed
        async with factory() as s:
            await seed(s)

        # Count after second seed — must equal first count (clear-then-seed strategy)
        async with factory() as s:
            count_2 = (
                await s.execute(
                    select(func.count()).where(
                        Practitioner.email.like(f"%@{SEED_EMAIL_DOMAIN}")
                    )
                )
            ).scalar_one()

        assert count_1 == count_2, (
            f"Seed is not idempotent: first run produced {count_1} practitioners, "
            f"second run produced {count_2}."
        )
        assert count_1 == len(PRACTITIONER_NAMES), (
            f"Expected exactly {len(PRACTITIONER_NAMES)} practitioners, got {count_1}."
        )


@pytest.mark.integration
class TestSeedSourceCoverage:
    async def test_all_four_signal_sources_are_represented(self, pg_engine: AsyncEngine):
        """
        Scenario: Seeded data spans all signal sources
          Given a freshly seeded database (tables created by pg_engine fixture)
          When querying skill_profile_events by source
          Then 'certification', 'self_assessment', 'quiz_attempt', and
               'project_history' are all represented
        """
        factory = _session_factory(pg_engine)

        async with factory() as s:
            await seed(s)

        async with factory() as s:
            rows = (
                await s.execute(
                    select(SkillProfileEvent.source).distinct()
                )
            ).scalars().all()

        present_sources = set(rows)
        required_sources = {
            "certification",
            "self_assessment",
            "quiz_attempt",
            "project_history",
        }
        missing = required_sources - present_sources
        assert not missing, (
            f"Seed data is missing these signal sources: {missing}"
        )
