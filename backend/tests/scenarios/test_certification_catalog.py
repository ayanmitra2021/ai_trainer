"""Step 2.2 — Certification catalog scenarios (integration tests).

Scenario: The seeded catalog spans more than one provider.
Scenario: Every certification maps to at least one skill.
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.db.models import (
    Certification,
    CertificationSkill,
)
from seed.generate import seed


def _session_factory(engine: AsyncEngine) -> async_sessionmaker:
    """Committed session factory — seed() needs to commit."""
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.mark.integration
class TestCertificationCatalogSeed:
    async def test_seeded_catalog_spans_multiple_providers(self, pg_engine: AsyncEngine):
        """
        Scenario: The seeded catalog spans more than one provider.
          Given a freshly seeded database
          When querying certifications joined to certification_providers
          Then at least four distinct providers are represented
        """
        factory = _session_factory(pg_engine)

        # Given — run the seed (commits internally, idempotent)
        async with factory() as s:
            await seed(s)

        # When
        async with factory() as s:
            result = await s.execute(
                select(func.count(func.distinct(Certification.provider_id)))
            )
            distinct_provider_count = result.scalar_one()

        # Then
        assert distinct_provider_count >= 4, (
            f"Expected at least 4 distinct providers, got {distinct_provider_count}"
        )

    async def test_every_certification_maps_to_at_least_one_skill(
        self, pg_engine: AsyncEngine
    ):
        """
        Scenario: Every certification maps to at least one skill.
          Given the seeded catalog
          When checking certification_skills
          Then no certification is orphaned with zero mapped skills
        """
        factory = _session_factory(pg_engine)

        # Given — run the seed (idempotent)
        async with factory() as s:
            await seed(s)

        # When — find certifications with no skill mappings
        async with factory() as s:
            cert_result = await s.execute(select(Certification.id, Certification.code))
            all_certs = cert_result.all()

            orphaned = []
            for cert_id, cert_code in all_certs:
                count_result = await s.execute(
                    select(func.count()).where(CertificationSkill.certification_id == cert_id)
                )
                count = count_result.scalar_one()
                if count == 0:
                    orphaned.append(cert_code)

        # Then
        assert len(orphaned) == 0, (
            f"These certifications have zero skill mappings: {orphaned}. "
            "An advisor recommendation with nothing to build a path from is a dead end."
        )
