"""Step 10.1 — Certification exam domains data model & seed data.

Scenario 1: Every active certification has at least 3 domain rows.
  Given a freshly seeded database
  When querying certification_domains grouped by certification_id
  Then every active certification has at least 3 associated domain rows.

Scenario 2: Domain weights sum to 100 per certification.
  Given a freshly seeded database
  When summing weight_pct for each certification's domains
  Then the sum is within ±1 of 100 for every certification group
  (±1 tolerance accommodates rounding differences between providers).

Scenario 3: Creating a profile without a certification_id returns 422.
  Given a logged-in practitioner
  When POST /practitioners/{id}/profiles is called with certification_id absent or null
  Then the API returns 422 (validation error), not 201 or 400.
  The DB column remains nullable; the enforcement is at the API layer only.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.db.models import (
    Certification,
    CertificationDomain,
    Practitioner,
)
from app.db.session import get_db
from app.main import app
from seed.generate import seed
from tests.conftest import apply_admin_auth_overrides, admin_session_info  # noqa: F401


# ── helpers ───────────────────────────────────────────────────────────────────


def _session_factory(engine: AsyncEngine) -> async_sessionmaker:
    """Committed session factory for integration tests."""
    return async_sessionmaker(engine, expire_on_commit=False)


# ── Scenario 1 & 2 — seeded domain data ───────────────────────────────────────


@pytest.mark.integration
class TestCertificationDomainsSeed:
    """Integration tests that run the full seed against a real Postgres DB."""

    async def test_every_active_cert_has_at_least_3_domains(
        self, pg_engine: AsyncEngine
    ):
        """
        Scenario: Every active certification has at least 3 domain rows.
          Given a freshly seeded database
          When querying certification_domains grouped by certification_id
          Then every active certification has at least 3 associated domain rows
        """
        factory = _session_factory(pg_engine)

        # Given — seed (idempotent)
        async with factory() as s:
            await seed(s)

        # When — find active certs and their domain counts
        async with factory() as s:
            active_cert_result = await s.execute(
                select(Certification.id, Certification.code).where(
                    Certification.is_active == True  # noqa: E712
                )
            )
            active_certs = active_cert_result.all()
            assert len(active_certs) > 0, "No active certifications found in seed"

            under_threshold: list[str] = []
            for cert_id, cert_code in active_certs:
                count_result = await s.execute(
                    select(func.count()).where(
                        CertificationDomain.certification_id == cert_id
                    )
                )
                domain_count = count_result.scalar_one()
                if domain_count < 3:
                    under_threshold.append(
                        f"{cert_code} ({domain_count} domains)"
                    )

        # Then
        assert len(under_threshold) == 0, (
            "These active certifications have fewer than 3 domain rows: "
            f"{under_threshold}. "
            "Every cert needs domains for the gap chart and item tagging to work."
        )

    async def test_domain_weights_sum_to_100_per_cert(
        self, pg_engine: AsyncEngine
    ):
        """
        Scenario: Domain weights sum to 100 per certification.
          Given a freshly seeded database
          When summing weight_pct for each certification's domains
          Then the sum is within ±1 of 100 for every certification group
        """
        factory = _session_factory(pg_engine)

        # Given — seed (idempotent)
        async with factory() as s:
            await seed(s)

        # When — compute domain weight sums per cert
        async with factory() as s:
            active_cert_result = await s.execute(
                select(Certification.id, Certification.code).where(
                    Certification.is_active == True  # noqa: E712
                )
            )
            active_certs = active_cert_result.all()

            # Only check certs that have domain rows
            bad_sums: list[str] = []
            for cert_id, cert_code in active_certs:
                sum_result = await s.execute(
                    select(func.sum(CertificationDomain.weight_pct)).where(
                        CertificationDomain.certification_id == cert_id
                    )
                )
                total = sum_result.scalar_one()
                if total is None:
                    continue  # no domains seeded for this cert — caught by scenario 1
                total_float = float(total)
                if not (99.0 <= total_float <= 101.0):
                    bad_sums.append(
                        f"{cert_code}: sum={total_float:.2f}% (must be 99–101%)"
                    )

        # Then
        assert len(bad_sums) == 0, (
            "Domain weights do not sum to 100% (±1) for these certifications: "
            f"{bad_sums}"
        )


# ── Scenario 3 — API-layer enforcement of certification_id ────────────────────


@pytest_asyncio.fixture
async def api_client(db_session: AsyncSession, admin_session_info):
    """FastAPI test client wired to SQLite in-memory DB with admin auth."""

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    apply_admin_auth_overrides(app, admin_session_info)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def practitioner(db_session: AsyncSession) -> Practitioner:
    """A minimal practitioner in the in-memory DB for API tests."""
    p = Practitioner(
        id=str(uuid.uuid4()),
        name="Domain Test User",
        email=f"domain-test-{uuid.uuid4().hex[:8]}@example.com",
        role="Consultant",
        practice="AI&E",
        seniority_level="mid",
    )
    db_session.add(p)
    await db_session.flush()
    return p


class TestProfileCertificationRequired:
    """API-layer scenarios — run against the SQLite in-memory DB (no live API key)."""

    async def test_create_profile_without_cert_id_returns_422(
        self, api_client: AsyncClient, practitioner: Practitioner
    ):
        """
        Scenario: Creating a profile without a certification_id returns 422.
          Given a logged-in practitioner
          When POST /practitioners/{id}/profiles is called with certification_id absent
          Then the API returns 422 (Pydantic validation error)
        """
        # When — no certification_id in body
        response = await api_client.post(
            f"/api/v1/practitioners/{practitioner.id}/profiles",
            json={"name": "My Test Profile"},
        )

        # Then
        assert response.status_code == 422, (
            f"Expected 422 (validation error) when certification_id is absent, "
            f"got {response.status_code}: {response.text}"
        )

    async def test_create_profile_with_explicit_null_cert_id_returns_422(
        self, api_client: AsyncClient, practitioner: Practitioner
    ):
        """
        Scenario: Creating a profile with certification_id=null returns 422.
          Given a logged-in practitioner
          When POST /practitioners/{id}/profiles is called with certification_id=null
          Then the API returns 422 (Pydantic validation error)

        Note: The DB column is nullable so existing rows are not disrupted.
        The enforcement is strictly at the API layer — the test confirms the
        validation error fires before the DB is touched.
        """
        # When — explicit null
        response = await api_client.post(
            f"/api/v1/practitioners/{practitioner.id}/profiles",
            json={"name": "My Test Profile", "certification_id": None},
        )

        # Then
        assert response.status_code == 422, (
            f"Expected 422 (validation error) when certification_id is null, "
            f"got {response.status_code}: {response.text}"
        )
