"""Step 10.2 — Domain versioning data model: live-refreshable domain versions.

Scenario 1: Every active certification has exactly one is_current=true version row.
  Given a freshly seeded database
  When querying certification_domain_versions
  Then every active certification that has domain rows has exactly one version
  row with is_current = true.

Scenario 2: Every certification_domains row has a non-null domain_version_id.
  Given a freshly seeded database
  When querying certification_domains
  Then no row has domain_version_id = NULL — every domain is linked to a version.

Scenario 3: Inserting a second is_current=true row for the same cert is rejected.
  Given a certification with one is_current=true version row
  When a second is_current=true row is inserted for the same cert
  Then the DB raises an IntegrityError (partial unique index fires on Postgres;
  regular unique index fires on SQLite — both reject the duplicate).
  NOTE: This is an integration test — the partial unique index that provides the
  correct semantics is created by Postgres's dialect-specific index DDL.

Additional API scenarios (unit-level):
  Scenario 4: GET /admin/cert-domain-versions requires admin role.
    Given a non-admin (leadership) session
    When GET /admin/cert-domain-versions is called
    Then the response is 403.

  Scenario 5: GET /admin/cert-domain-proposals filters by status.
    Given two proposals with different statuses
    When GET /admin/cert-domain-proposals?status=approved is called
    Then only the approved proposal is returned.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.db.models import (
    AgentRun,
    Certification,
    CertificationDomain,
    CertificationDomainProposal,
    CertificationDomainVersion,
    CertificationProvider,
)
from app.db.session import get_db
from app.main import app
from seed.generate import seed
from tests.conftest import (  # noqa: F401
    admin_session_info,
    apply_admin_auth_overrides,
    apply_leadership_auth_overrides,
    leadership_session_info,
)


# ── helpers ───────────────────────────────────────────────────────────────────


def _session_factory(engine: AsyncEngine) -> async_sessionmaker:
    """Committed session factory for integration tests."""
    return async_sessionmaker(engine, expire_on_commit=False)


# ── Scenario 1 & 2 — seeded domain versioning ─────────────────────────────────


@pytest.mark.integration
class TestDomainVersionSeed:
    """Integration tests that run the full seed against a real Postgres DB."""

    async def test_every_active_cert_has_exactly_one_current_version(
        self, pg_engine: AsyncEngine
    ):
        """
        Scenario 1: Every active certification has exactly one is_current=true version row.
          Given a freshly seeded database
          When querying certification_domain_versions grouped by certification_id
          Then every active cert that has domain rows has exactly one is_current=true row
        """
        factory = _session_factory(pg_engine)

        # Given — seed (idempotent)
        async with factory() as s:
            await seed(s)

        # When — find active certs and their domain version counts
        async with factory() as s:
            active_cert_result = await s.execute(
                select(Certification.id, Certification.code).where(
                    Certification.is_active == True  # noqa: E712
                )
            )
            active_certs = active_cert_result.all()
            assert len(active_certs) > 0, "No active certifications found in seed"

            problems: list[str] = []
            for cert_id, cert_code in active_certs:
                # Check how many is_current=True versions exist for this cert
                current_result = await s.execute(
                    select(CertificationDomainVersion).where(
                        CertificationDomainVersion.certification_id == cert_id,
                        CertificationDomainVersion.is_current == True,  # noqa: E712
                    )
                )
                current_versions = current_result.scalars().all()

                # Check whether this cert has any domains at all
                domain_count_result = await s.execute(
                    select(CertificationDomain).where(
                        CertificationDomain.certification_id == cert_id
                    )
                )
                has_domains = len(domain_count_result.scalars().all()) > 0

                if has_domains and len(current_versions) != 1:
                    problems.append(
                        f"{cert_code}: expected 1 is_current=True version, "
                        f"found {len(current_versions)}"
                    )

        # Then
        assert len(problems) == 0, (
            "These certifications do not have exactly one current domain version:\n"
            + "\n".join(problems)
        )

    async def test_every_domain_row_has_non_null_version_id(
        self, pg_engine: AsyncEngine
    ):
        """
        Scenario 2: Every certification_domains row has a non-null domain_version_id.
          Given a freshly seeded database
          When querying all certification_domains rows
          Then no row has domain_version_id = NULL — every domain is linked to a version
        """
        factory = _session_factory(pg_engine)

        # Given — seed (idempotent)
        async with factory() as s:
            await seed(s)

        # When
        async with factory() as s:
            unlinked_result = await s.execute(
                select(CertificationDomain).where(
                    CertificationDomain.domain_version_id == None  # noqa: E711
                )
            )
            unlinked = unlinked_result.scalars().all()

        # Then
        assert len(unlinked) == 0, (
            f"Found {len(unlinked)} certification_domains row(s) with NULL "
            f"domain_version_id after seeding.  Every domain row must be linked "
            f"to a version (via domain_version_id) so profiles can be frozen "
            f"against a specific snapshot of exam domain data."
        )


# ── Scenario 3 — partial unique index enforcement ─────────────────────────────


@pytest.mark.integration
class TestCurrentVersionUniqueConstraint:
    """Integration test: at most one is_current=True version per cert (DB-level guard)."""

    async def test_second_current_version_for_same_cert_is_rejected(
        self, pg_engine: AsyncEngine
    ):
        """
        Scenario 3: Inserting a second is_current=true row for the same cert is rejected.
          Given a certification with one is_current=true version row
          When a second is_current=true row is inserted for the same cert
          Then the DB raises an IntegrityError (unique index violation).

        On Postgres: the partial unique index
          UNIQUE (certification_id) WHERE is_current = true
        correctly allows multiple is_current=false rows while rejecting a second
        is_current=true row.

        On SQLite (unit tests): the unique index on certification_id applies
        unconditionally, so this test must run against a real Postgres instance.
        """
        factory = _session_factory(pg_engine)

        async with factory() as s:
            # Create a minimal provider + cert for this test
            provider = CertificationProvider(
                id=str(uuid.uuid4()),
                name=f"TestProvider-{uuid.uuid4().hex[:6]}",
            )
            s.add(provider)
            await s.flush()

            cert = Certification(
                id=str(uuid.uuid4()),
                provider_id=provider.id,
                code=f"TEST-{uuid.uuid4().hex[:6]}",
                name="Test Cert for Uniqueness Check",
                level="foundational",
                requires_coding_background=False,
                is_active=True,
            )
            s.add(cert)
            await s.flush()

            # Insert first version — is_current=True
            v1 = CertificationDomainVersion(
                id=str(uuid.uuid4()),
                certification_id=cert.id,
                version_label="v1",
                is_current=True,
                source_notes="First version",
            )
            s.add(v1)
            await s.flush()

            # Insert second version — also is_current=True for the SAME cert.
            # This must be rejected by the partial unique index.
            v2 = CertificationDomainVersion(
                id=str(uuid.uuid4()),
                certification_id=cert.id,
                version_label="v2",
                is_current=True,
                source_notes="Second version — should be rejected",
            )
            s.add(v2)

            with pytest.raises(IntegrityError) as exc_info:
                await s.flush()

            # Confirm the error is the uniqueness violation (not some other error)
            err_str = str(exc_info.value).lower()
            assert any(
                keyword in err_str
                for keyword in ("unique", "duplicate", "constraint")
            ), (
                f"Expected a unique-constraint IntegrityError but got a different "
                f"error: {exc_info.value}"
            )


# ── Scenario 4 & 5 — API route tests (unit-level, SQLite) ────────────────────


@pytest_asyncio.fixture
async def api_client_admin(db_session: AsyncSession, admin_session_info):
    """FastAPI test client with full admin auth and SQLite in-memory DB."""

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    apply_admin_auth_overrides(app, admin_session_info)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def api_client_leadership(db_session: AsyncSession, leadership_session_info):
    """FastAPI test client with leadership auth — require_admin should still reject."""

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    apply_leadership_auth_overrides(app, leadership_session_info)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


class TestCertDomainVersionsAPI:
    """API-level tests running against SQLite in-memory DB (no live API key needed)."""

    async def test_get_versions_requires_admin_role(
        self, api_client_leadership: AsyncClient
    ):
        """
        Scenario 4: GET /admin/cert-domain-versions requires admin role.
          Given a leadership (non-admin) session
          When GET /admin/cert-domain-versions is called
          Then the response is 403
        """
        response = await api_client_leadership.get(
            "/api/v1/admin/cert-domain-versions"
        )
        assert response.status_code == 403, (
            f"Expected 403 (leadership cannot access admin-only endpoint), "
            f"got {response.status_code}: {response.text}"
        )

    async def test_get_versions_returns_empty_list_when_no_versions(
        self, api_client_admin: AsyncClient
    ):
        """
        Scenario 4b: GET /admin/cert-domain-versions returns an empty list on fresh DB.
          Given an empty database (no domain versions seeded)
          When GET /admin/cert-domain-versions is called as admin
          Then the response is 200 with an empty list
        """
        response = await api_client_admin.get("/api/v1/admin/cert-domain-versions")
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        assert response.json() == [], (
            f"Expected empty list on fresh DB, got: {response.json()}"
        )

    async def test_get_proposals_filters_by_status(
        self, api_client_admin: AsyncClient, db_session: AsyncSession
    ):
        """
        Scenario 5: GET /admin/cert-domain-proposals filters by status.
          Given two proposals with different statuses (pending_review and approved)
          When GET /admin/cert-domain-proposals?status=approved is called
          Then only the approved proposal is returned
        """
        # Setup: insert minimal provider + cert + agent_run + two proposals
        provider = CertificationProvider(
            id=str(uuid.uuid4()),
            name=f"TestProvider-{uuid.uuid4().hex[:6]}",
        )
        db_session.add(provider)

        cert = Certification(
            id=str(uuid.uuid4()),
            provider_id=provider.id,
            code=f"TPROP-{uuid.uuid4().hex[:6]}",
            name="Test Cert for Proposal Filter",
            level="foundational",
            requires_coding_background=False,
            is_active=True,
        )
        db_session.add(cert)

        # agent_run is required for proposal FK
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        agent_run = AgentRun(
            id=str(uuid.uuid4()),
            agent_name="cert_domain_discovery",
            input={},
            output={},
            model_used="claude-sonnet-5",
            tokens_input=100,
            tokens_output=50,
            latency_ms=500,
            status="success",
            started_at=now,
            completed_at=now,
        )
        db_session.add(agent_run)
        await db_session.flush()

        # Two proposals: one pending, one approved
        pending = CertificationDomainProposal(
            id=str(uuid.uuid4()),
            certification_id=cert.id,
            cert_code=cert.code,
            cert_name=cert.name,
            proposed_domains=[{"sequence_order": 1, "domain_name": "Domain A",
                                "domain_description": "Desc A", "weight_pct": 100}],
            source_notes="Pending proposal",
            agent_run_id=agent_run.id,
            status="pending_review",
        )
        db_session.add(pending)

        approved = CertificationDomainProposal(
            id=str(uuid.uuid4()),
            certification_id=cert.id,
            cert_code=cert.code,
            cert_name=cert.name,
            proposed_domains=[{"sequence_order": 1, "domain_name": "Domain B",
                                "domain_description": "Desc B", "weight_pct": 100}],
            source_notes="Approved proposal",
            agent_run_id=agent_run.id,
            status="approved",
        )
        db_session.add(approved)
        await db_session.flush()

        # When — request only approved proposals
        response = await api_client_admin.get(
            "/api/v1/admin/cert-domain-proposals?status=approved"
        )

        # Then
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert len(data) == 1, (
            f"Expected exactly 1 approved proposal, got {len(data)}: {data}"
        )
        assert data[0]["status"] == "approved"
        assert data[0]["source_notes"] == "Approved proposal"
        assert data[0]["id"] == approved.id

    async def test_get_proposals_requires_admin_role(
        self, api_client_leadership: AsyncClient
    ):
        """
        Scenario 5b: GET /admin/cert-domain-proposals requires admin role.
          Given a leadership session
          When GET /admin/cert-domain-proposals is called
          Then the response is 403
        """
        response = await api_client_leadership.get(
            "/api/v1/admin/cert-domain-proposals"
        )
        assert response.status_code == 403, (
            f"Expected 403 (leadership cannot access admin-only endpoint), "
            f"got {response.status_code}: {response.text}"
        )
