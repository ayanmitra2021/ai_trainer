"""
Scenario tests — Step 0.3: Synthetic seed data generator.

These are integration tests that require a running Postgres container.
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
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Practitioner, SkillProfileEvent
from seed.generate import seed, SEED_EMAIL_DOMAIN, PRACTITIONER_NAMES


def _test_engine():
    test_url = os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://mastery:mastery@localhost:5432/mastery_pulse",
    )
    return create_async_engine(test_url, echo=False)


@pytest_asyncio.fixture(scope="module")
async def seeded_session():
    """Run the seed once; yield a session; dispose on teardown."""
    engine = _test_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        await seed(session)

    # Yield a fresh session for assertions
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.integration
class TestSeedIdempotency:
    async def test_second_seed_does_not_double_practitioners(self):
        """
        Scenario: Seeding is idempotent
          Given an already-seeded database
          When the seed script runs again
          Then the practitioner count doesn't double
        """
        engine = _test_engine()
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        try:
            # First seed
            async with session_factory() as s:
                await seed(s)

            # Count after first seed
            async with session_factory() as s:
                count_1 = (
                    await s.execute(
                        select(func.count()).where(
                            Practitioner.email.like(f"%@{SEED_EMAIL_DOMAIN}")
                        )
                    )
                ).scalar_one()

            # Second seed
            async with session_factory() as s:
                await seed(s)

            # Count after second seed — must equal first count (clear-then-seed strategy)
            async with session_factory() as s:
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
        finally:
            await engine.dispose()


@pytest.mark.integration
class TestSeedSourceCoverage:
    async def test_all_four_signal_sources_are_represented(self):
        """
        Scenario: Seeded data spans all signal sources
          Given a freshly seeded database
          When querying skill_profile_events by source
          Then 'certification', 'self_assessment', 'quiz_attempt', and
               'project_history' are all represented
        """
        engine = _test_engine()
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        try:
            async with session_factory() as s:
                await seed(s)

            async with session_factory() as s:
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
        finally:
            await engine.dispose()
