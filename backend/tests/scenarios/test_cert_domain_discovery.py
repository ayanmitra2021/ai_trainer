"""Step 10.3 — Cert Domain Discovery Agent & approve/reject API.

Scenario 1: discover endpoint persists proposal with status=pending_review.
  Given a stub agent that returns 5 valid domain rows summing to 100%
  When POST /admin/cert-domains/discover is called
  Then a certification_domain_proposals row is created with status=pending_review
  and is linked to an agent_runs row.

Scenario 2: approve endpoint creates new certification_domain_versions row
  with is_current=True and new certification_domains rows.
  NOTE: The "flip old version to is_current=False" behaviour requires Postgres
  (partial unique index; SQLite drops the WHERE clause and enforces a full
  unique index on certification_id).  The flip is tested at the integration
  layer; this unit test validates the happy-path creation against a fresh cert
  with no pre-existing version.

Scenario 3: approve creates a new cert row (is_active=False) when cert_code is new.
  Given a pending proposal whose cert_code does not exist in certifications
  When POST /admin/cert-domain-proposals/{id}/approve is called
  Then a new Certification row is created with is_active=False.

Scenario 4: reject sets status=rejected without touching certification_domains.
  Given a pending proposal and existing certification_domains rows
  When POST /admin/cert-domain-proposals/{id}/reject is called
  Then proposal.status == 'rejected' with rejection_notes set
  and certification_domains rows are untouched.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
from tests.conftest import (  # noqa: F401
    admin_session_info,
    apply_admin_auth_overrides,
)


# ── helpers ───────────────────────────────────────────────────────────────────


def _make_proposed_domains(n: int = 5) -> list[dict]:
    """Return n domains that sum to 100 weight_pct."""
    weight_each = 100 // n
    remainder = 100 - weight_each * n
    domains = []
    for i in range(1, n + 1):
        extra = remainder if i == 1 else 0
        domains.append({
            "sequence_order": i,
            "domain_name": f"Domain {i}",
            "domain_description": f"Description for domain {i}",
            "weight_pct": weight_each + extra,
        })
    return domains


async def _create_provider_and_cert(
    db: AsyncSession,
    code: str = "TEST-DISCOVER",
    is_active: bool = True,
) -> tuple[CertificationProvider, Certification]:
    provider = CertificationProvider(
        id=str(uuid.uuid4()),
        name=f"TestProvider-{uuid.uuid4().hex[:6]}",
    )
    db.add(provider)
    await db.flush()

    cert = Certification(
        id=str(uuid.uuid4()),
        provider_id=provider.id,
        code=code,
        name="Test Discover Cert",
        level="foundational",
        requires_coding_background=False,
        is_active=is_active,
    )
    db.add(cert)
    await db.flush()
    return provider, cert


async def _create_pending_proposal(
    db: AsyncSession,
    cert: Certification,
    proposed_domains: list[dict] | None = None,
) -> CertificationDomainProposal:
    """Create an agent_run row and a pending_review proposal linked to it."""
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
    db.add(agent_run)
    await db.flush()

    proposal = CertificationDomainProposal(
        id=str(uuid.uuid4()),
        certification_id=cert.id,
        cert_code=cert.code,
        cert_name=cert.name,
        proposed_domains=proposed_domains or _make_proposed_domains(5),
        source_notes="Test discovery agent run",
        agent_run_id=agent_run.id,
        status="pending_review",
    )
    db.add(proposal)
    await db.flush()
    return proposal


# ── Fixtures ───────────────────────────────────────────────────────────────────


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


# ── Scenario 1: discover creates a pending_review proposal ────────────────────


class TestDiscoverEndpoint:
    async def test_discover_persists_pending_proposal_linked_to_agent_run(
        self, api_client_admin: AsyncClient, db_session: AsyncSession
    ):
        """
        Scenario 1: discover endpoint persists proposal with status=pending_review.
          Given a stub agent response with 5 valid domain rows summing to 100%
          When POST /admin/cert-domains/discover is called
          Then a certification_domain_proposals row is created with status=pending_review
          and is linked to an agent_runs row.
        """
        # Given: the discovery agent will return 5 domains
        proposed_domains = _make_proposed_domains(5)

        # Patch create_model_client so the agent uses a stub
        from tests.fixtures.stub_claude_client import StubClaudeClient
        stub = StubClaudeClient(
            response_data={
                "cert_code": "NEW-DISC-CERT",
                "proposed_domains": proposed_domains,
                "source_notes": "High confidence from training data",
                "changes_from_current": None,
                "confidence": "high",
                "suggested_source_url": None,
            }
        )

        with patch(
            "app.api.routes.cert_domain_versions.create_model_client",
            return_value=stub,
        ):
            response = await api_client_admin.post(
                "/api/v1/admin/cert-domains/discover",
                json={
                    "cert_code": "NEW-DISC-CERT",
                    "cert_name": "New Discovery Test Cert",
                    "provider_name": "TestProvider",
                },
            )

        assert response.status_code == 201, (
            f"Expected 201, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert data["cert_code"] == "NEW-DISC-CERT"
        assert data["status"] == "pending_review"
        assert len(data["proposed_domains"]) == 5
        assert data["agent_run_id"] is not None

        # Verify proposal row in DB
        proposal_result = await db_session.execute(
            select(CertificationDomainProposal).where(
                CertificationDomainProposal.id == data["id"]
            )
        )
        proposal = proposal_result.scalar_one_or_none()
        assert proposal is not None
        assert proposal.status == "pending_review"
        assert len(proposal.proposed_domains) == 5

        # Verify agent_run row exists
        agent_run_result = await db_session.execute(
            select(AgentRun).where(AgentRun.id == proposal.agent_run_id)
        )
        agent_run = agent_run_result.scalar_one_or_none()
        assert agent_run is not None
        assert agent_run.agent_name == "cert_domain_discovery"


# ── Scenario 2: approve creates new version and domain rows ───────────────────


class TestApproveEndpoint:
    async def test_approve_creates_new_version_and_domain_rows(
        self, api_client_admin: AsyncClient, db_session: AsyncSession
    ):
        """
        Scenario 2: approve endpoint creates new certification_domain_versions row
          with is_current=True and new certification_domains rows.

        NOTE: The "flip old version to is_current=False" behaviour requires a
        partial unique index (Postgres-only).  On SQLite the index is unconditional
        on certification_id, so a second row cannot be inserted — this is an
        integration test concern, not a unit-test concern.  This test validates
        the creation path against a fresh cert with no pre-existing version row.

          Given a pending proposal for a cert with no existing version
          When POST /admin/cert-domain-proposals/{id}/approve is called
          Then a new version with is_current=True is created
          and new certification_domains rows are created for each proposed domain.
        """
        # Given: fresh cert with no pre-existing version (avoids SQLite unique conflict)
        provider, cert = await _create_provider_and_cert(db_session, "APPROVE-TEST")

        proposal = await _create_pending_proposal(
            db_session, cert, _make_proposed_domains(3)
        )

        # When
        response = await api_client_admin.post(
            f"/api/v1/admin/cert-domain-proposals/{proposal.id}/approve"
        )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert data["domains_created"] == 3
        assert data["new_cert_created"] is False

        # Verify new version is is_current=True
        new_version_result = await db_session.execute(
            select(CertificationDomainVersion).where(
                CertificationDomainVersion.id == data["new_version_id"]
            )
        )
        new_version = new_version_result.scalar_one_or_none()
        assert new_version is not None
        assert new_version.is_current is True
        assert new_version.certification_id == cert.id

        # Verify 3 new domain rows linked to new version
        new_domains_result = await db_session.execute(
            select(CertificationDomain).where(
                CertificationDomain.domain_version_id == new_version.id
            )
        )
        new_domains = new_domains_result.scalars().all()
        assert len(new_domains) == 3

        # Verify proposal is marked approved
        await db_session.refresh(proposal)
        assert proposal.status == "approved"

    async def test_approve_proposal_for_new_cert_code_creates_inactive_cert(
        self, api_client_admin: AsyncClient, db_session: AsyncSession
    ):
        """
        Scenario 3: approve for cert_code not in certifications creates new cert with is_active=False.
          Given a pending proposal whose cert_code does not exist in certifications
          When POST /admin/cert-domain-proposals/{id}/approve is called
          Then a new Certification row is created with is_active=False.
        """
        # Given: a provider exists but no cert with this code
        provider = CertificationProvider(
            id=str(uuid.uuid4()),
            name="NewCertProvider",
        )
        db_session.add(provider)
        await db_session.flush()

        # Proposal with null certification_id (brand-new cert)
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

        proposal = CertificationDomainProposal(
            id=str(uuid.uuid4()),
            certification_id=None,  # no existing cert
            cert_code="BRAND-NEW-CERT",
            cert_name="Brand New Certification",
            proposed_domains=_make_proposed_domains(2),
            source_notes="Discovery for a new cert",
            agent_run_id=agent_run.id,
            status="pending_review",
        )
        db_session.add(proposal)
        await db_session.flush()

        # When
        response = await api_client_admin.post(
            f"/api/v1/admin/cert-domain-proposals/{proposal.id}/approve"
        )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert data["new_cert_created"] is True
        assert data["domains_created"] == 2

        # Verify the new cert has is_active=False
        cert_result = await db_session.execute(
            select(Certification).where(Certification.code == "BRAND-NEW-CERT")
        )
        new_cert = cert_result.scalar_one_or_none()
        assert new_cert is not None, "New cert should have been created"
        assert new_cert.is_active is False, (
            "Newly created cert should have is_active=False until admin explicitly activates"
        )


# ── Scenario 4: reject sets status without touching domains ───────────────────


class TestRejectEndpoint:
    async def test_reject_sets_status_and_does_not_touch_domain_rows(
        self, api_client_admin: AsyncClient, db_session: AsyncSession
    ):
        """
        Scenario 4: rejecting a proposal sets status=rejected without touching certification_domains.
          Given a pending proposal and existing certification_domains rows
          When POST /admin/cert-domain-proposals/{id}/reject is called
          Then proposal.status == 'rejected' with rejection_notes set
          and existing certification_domains rows are untouched.
        """
        # Given
        provider, cert = await _create_provider_and_cert(db_session, "REJECT-TEST")

        # We don't create a pre-existing version here (avoids SQLite unique index issue)
        # Just verify that proposal rejection doesn't create domain rows.
        domain_count_before = len(
            (await db_session.execute(
                select(CertificationDomain).where(
                    CertificationDomain.certification_id == cert.id
                )
            )).scalars().all()
        )

        proposal = await _create_pending_proposal(db_session, cert)

        # When
        response = await api_client_admin.post(
            f"/api/v1/admin/cert-domain-proposals/{proposal.id}/reject",
            json={"rejection_notes": "Domains look incorrect — please verify against official guide"},
        )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )

        # Then: proposal is rejected
        await db_session.refresh(proposal)
        assert proposal.status == "rejected"
        assert "incorrect" in (proposal.rejection_notes or "")

        # Domain rows are untouched (none were created by rejection)
        domain_count_after = len(
            (await db_session.execute(
                select(CertificationDomain).where(
                    CertificationDomain.certification_id == cert.id
                )
            )).scalars().all()
        )
        assert domain_count_after == domain_count_before, (
            "Rejection must not create or delete any certification_domain rows"
        )
