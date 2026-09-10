"""F-MOD-001 — Profile Name PATCH endpoint.

Behavioral expectations for:
  PATCH /api/v1/practitioners/{practitioner_id}/profiles/{profile_id}/name

All tests run against the in-memory SQLite database via ASGI transport — no Postgres required.
No mocks; every test exercises real routes and real DB writes.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.session import get_session, require_any_authenticated
from app.db.models import (
    Certification,
    CertificationProvider,
    Practitioner,
    PractitionerProfile,
)
from app.db.session import get_db
from app.main import app
from tests.conftest import apply_admin_auth_overrides, make_practitioner_session

# ── Shared helpers ────────────────────────────────────────────────────────────


async def _make_practitioner(db: AsyncSession) -> Practitioner:
    p = Practitioner(
        id=str(uuid.uuid4()),
        name="Name Patch Test User",
        email=f"namepatch-{uuid.uuid4().hex[:8]}@example.com",
        created_at=datetime.now(UTC),
    )
    db.add(p)
    await db.flush()
    return p


async def _make_cert(db: AsyncSession) -> Certification:
    provider = CertificationProvider(
        id=str(uuid.uuid4()),
        name="NamePatchCorp",
    )
    db.add(provider)
    await db.flush()

    cert = Certification(
        id=str(uuid.uuid4()),
        provider_id=provider.id,
        code="NPC-F",
        name="NamePatchCorp Foundations",
        level="foundational",
        requires_coding_background=False,
        is_active=True,
        last_verified_at=datetime.now(UTC).date(),
    )
    db.add(cert)
    await db.flush()
    return cert


async def _make_profile(
    db: AsyncSession,
    practitioner_id: str,
    *,
    name: str = "Original Name",
    is_active: bool = True,
    is_locked: bool = False,
    certification_id: str | None = None,
    questionnaire_snapshot: dict | None = None,
) -> PractitionerProfile:
    profile = PractitionerProfile(
        id=str(uuid.uuid4()),
        practitioner_id=practitioner_id,
        name=name,
        is_active=is_active,
        is_locked=is_locked,
        certification_id=certification_id,
        questionnaire_snapshot=questionnaire_snapshot or {"writes_code": True},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(profile)
    await db.flush()
    return profile


# ── Client fixtures ───────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, admin_session_info):
    """Admin-authed AsyncClient — auth is bypassed via dependency override."""
    async def _get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_test_db
    apply_admin_auth_overrides(app, admin_session_info)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def no_auth_client(db_session: AsyncSession):
    """AsyncClient with NO auth override — real session check runs, returning 401."""
    async def _get_test_db():
        yield db_session

    # Override only the DB dep; auth deps are NOT overridden so they check for a cookie.
    app.dependency_overrides[get_db] = _get_test_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def wrong_prac_client(db_session: AsyncSession):
    """Client whose session practitioner_id does NOT match the URL practitioner_id."""
    async def _get_test_db():
        yield db_session

    other_session = make_practitioner_session("completely-different-practitioner-id")
    app.dependency_overrides[get_db] = _get_test_db
    app.dependency_overrides[get_session] = lambda: other_session
    app.dependency_overrides[require_any_authenticated] = lambda: other_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestPatchProfileNameHappyPath:
    """
    Given a valid practitioner session and an active profile owned by the caller,
    when PATCH .../profiles/{profile_id}/name is called with a valid name,
    then HTTP 200 is returned and the body is a ProfileRead with the updated name.
    """

    async def test_F_MOD_001_returns_200_with_updated_name(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        # Arrange
        practitioner = await _make_practitioner(db_session)
        profile = await _make_profile(db_session, practitioner.id, is_active=True, name="Old Name")
        await db_session.commit()

        # Act
        resp = await client.patch(
            f"/api/v1/practitioners/{practitioner.id}/profiles/{profile.id}/name",
            json={"name": "Brand New Name"},
        )

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Brand New Name"
        assert data["id"] == profile.id
        assert data["practitioner_id"] == practitioner.id

    async def test_F_MOD_001_response_shape_is_profile_read(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Response includes all ProfileRead fields, not just the name."""
        practitioner = await _make_practitioner(db_session)
        cert = await _make_cert(db_session)
        profile = await _make_profile(
            db_session,
            practitioner.id,
            is_active=True,
            certification_id=cert.id,
        )
        await db_session.commit()

        resp = await client.patch(
            f"/api/v1/practitioners/{practitioner.id}/profiles/{profile.id}/name",
            json={"name": "Renamed"},
        )

        assert resp.status_code == 200
        data = resp.json()
        # Verify ProfileRead shape: all required fields are present.
        for field in ("id", "practitioner_id", "name", "is_active",
                      "certification_id", "is_locked", "created_at", "updated_at"):
            assert field in data, f"Missing field: {field}"


class TestPatchProfileNameWhitespaceTrimming:
    """
    Given a valid name containing leading/trailing whitespace,
    when the endpoint is called,
    then the name is persisted with whitespace stripped.
    """

    async def test_F_MOD_001_name_trimmed_before_persistence(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        practitioner = await _make_practitioner(db_session)
        profile = await _make_profile(db_session, practitioner.id, is_active=True)
        await db_session.commit()

        resp = await client.patch(
            f"/api/v1/practitioners/{practitioner.id}/profiles/{profile.id}/name",
            json={"name": "  trimmed  "},
        )

        assert resp.status_code == 200
        # The stored name must be the stripped value, not the padded original.
        assert resp.json()["name"] == "trimmed"


class TestPatchProfileNameForbidden:
    """
    Given a valid session whose practitioner_id does NOT match the URL practitioner_id,
    when the endpoint is called,
    then HTTP 403 is returned.
    """

    async def test_F_MOD_001_wrong_practitioner_returns_403(
        self, wrong_prac_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        practitioner = await _make_practitioner(db_session)
        profile = await _make_profile(db_session, practitioner.id, is_active=True)
        await db_session.commit()

        resp = await wrong_prac_client.patch(
            f"/api/v1/practitioners/{practitioner.id}/profiles/{profile.id}/name",
            json={"name": "Unauthorized Name"},
        )

        assert resp.status_code == 403


class TestPatchProfileNameInactiveProfile:
    """
    Given an active session that owns a profile with is_active=False,
    when the endpoint is called,
    then HTTP 404 is returned.
    """

    async def test_F_MOD_001_inactive_profile_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        practitioner = await _make_practitioner(db_session)
        profile = await _make_profile(db_session, practitioner.id, is_active=False)
        await db_session.commit()

        resp = await client.patch(
            f"/api/v1/practitioners/{practitioner.id}/profiles/{profile.id}/name",
            json={"name": "New Name"},
        )

        assert resp.status_code == 404


class TestPatchProfileNameValidation:
    """
    Given a valid session, when the name field is empty, absent, or too long,
    then HTTP 422 is returned.
    """

    async def test_F_MOD_001_empty_name_returns_422(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        practitioner = await _make_practitioner(db_session)
        profile = await _make_profile(db_session, practitioner.id, is_active=True)
        await db_session.commit()

        resp = await client.patch(
            f"/api/v1/practitioners/{practitioner.id}/profiles/{profile.id}/name",
            json={"name": ""},
        )

        assert resp.status_code == 422

    async def test_F_MOD_001_missing_name_field_returns_422(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        practitioner = await _make_practitioner(db_session)
        profile = await _make_profile(db_session, practitioner.id, is_active=True)
        await db_session.commit()

        resp = await client.patch(
            f"/api/v1/practitioners/{practitioner.id}/profiles/{profile.id}/name",
            json={},
        )

        assert resp.status_code == 422

    async def test_F_MOD_001_name_exceeding_500_chars_returns_422(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        practitioner = await _make_practitioner(db_session)
        profile = await _make_profile(db_session, practitioner.id, is_active=True)
        await db_session.commit()

        too_long = "x" * 501

        resp = await client.patch(
            f"/api/v1/practitioners/{practitioner.id}/profiles/{profile.id}/name",
            json={"name": too_long},
        )

        assert resp.status_code == 422

    async def test_F_MOD_001_whitespace_only_name_returns_422(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """A name that is blank after stripping must be rejected with 422."""
        practitioner = await _make_practitioner(db_session)
        profile = await _make_profile(db_session, practitioner.id, is_active=True)
        await db_session.commit()

        resp = await client.patch(
            f"/api/v1/practitioners/{practitioner.id}/profiles/{profile.id}/name",
            json={"name": "   "},
        )

        assert resp.status_code == 422


class TestPatchProfileNameLockedProfile:
    """
    Given a valid session that owns an active profile where is_locked=True,
    when the endpoint is called with a valid name,
    then HTTP 200 is returned — the lock gate is NOT consulted by this endpoint.
    """

    async def test_F_MOD_001_locked_active_profile_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        practitioner = await _make_practitioner(db_session)
        profile = await _make_profile(
            db_session, practitioner.id, is_active=True, is_locked=True
        )
        await db_session.commit()

        resp = await client.patch(
            f"/api/v1/practitioners/{practitioner.id}/profiles/{profile.id}/name",
            json={"name": "Renamed Even Though Locked"},
        )

        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed Even Though Locked"
        # Confirm is_locked is still True — the endpoint doesn't change the lock.
        assert resp.json()["is_locked"] is True


class TestPatchProfileNameNoAuth:
    """
    Given no authenticated session (missing cookie),
    when the endpoint is called,
    then HTTP 401 is returned.
    """

    async def test_F_MOD_001_no_session_returns_401(
        self, no_auth_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        practitioner = await _make_practitioner(db_session)
        profile = await _make_profile(db_session, practitioner.id, is_active=True)
        await db_session.commit()

        resp = await no_auth_client.patch(
            f"/api/v1/practitioners/{practitioner.id}/profiles/{profile.id}/name",
            json={"name": "Unauthorized"},
        )

        assert resp.status_code == 401


class TestPatchProfileNameNotFound:
    """
    Given a profile_id that does not exist in the database,
    when the endpoint is called,
    then HTTP 404 is returned.
    """

    async def test_F_MOD_001_nonexistent_profile_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        practitioner = await _make_practitioner(db_session)
        await db_session.commit()

        nonexistent_id = str(uuid.uuid4())

        resp = await client.patch(
            f"/api/v1/practitioners/{practitioner.id}/profiles/{nonexistent_id}/name",
            json={"name": "Ghost Name"},
        )

        assert resp.status_code == 404


class TestPatchProfileNameFieldPreservation:
    """
    Given a successful name update,
    when the response is inspected,
    then is_locked, certification_id, questionnaire_snapshot, and is_active
    are identical to their pre-update values.
    """

    async def test_F_MOD_001_other_fields_unchanged_after_rename(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        practitioner = await _make_practitioner(db_session)
        cert = await _make_cert(db_session)
        snapshot = {"writes_code": True, "experience_years": 5}
        profile = await _make_profile(
            db_session,
            practitioner.id,
            name="Before Rename",
            is_active=True,
            is_locked=True,
            certification_id=cert.id,
            questionnaire_snapshot=snapshot,
        )
        await db_session.commit()

        resp = await client.patch(
            f"/api/v1/practitioners/{practitioner.id}/profiles/{profile.id}/name",
            json={"name": "After Rename"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "After Rename"
        # All other key fields must be identical to their pre-update values.
        assert data["is_locked"] is True
        assert data["certification_id"] == cert.id
        assert data["questionnaire_snapshot"] == snapshot
        assert data["is_active"] is True


class TestExistingPatchStillBlocksLockedProfiles:
    """
    Given the existing PATCH /api/v1/practitioners/{id}/profiles/{profile_id} route,
    when called with any body on a locked profile,
    then HTTP 403 is still returned — the new name endpoint does not alter this behavior.
    """

    async def test_F_MOD_001_existing_patch_still_returns_403_on_locked_profile(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        practitioner = await _make_practitioner(db_session)
        profile = await _make_profile(
            db_session, practitioner.id, is_active=True, is_locked=True
        )
        await db_session.commit()

        resp = await client.patch(
            f"/api/v1/practitioners/{practitioner.id}/profiles/{profile.id}",
            json={"name": "Should Be Blocked"},
        )

        assert resp.status_code == 403
        assert "locked" in resp.json()["detail"].lower()


class TestStartupEnvChecker:
    """
    Given DATABASE_URL is absent from the environment,
    when the startup env checker runs,
    then it raises a RuntimeError with code ERR_CDR_78_EX_CONFIG naming the variable.
    """

    def test_F_MOD_001_check_env_raises_when_database_url_absent(self) -> None:
        from config.env_check import check_env

        original = os.environ.pop("DATABASE_URL", None)
        try:
            with pytest.raises(RuntimeError) as exc_info:
                check_env()
            error_msg = str(exc_info.value)
            assert "ERR_CDR_78_EX_CONFIG" in error_msg
            assert "DATABASE_URL" in error_msg
        finally:
            if original is not None:
                os.environ["DATABASE_URL"] = original

    def test_F_MOD_001_check_env_passes_when_database_url_present(self) -> None:
        """When DATABASE_URL is set, check_env() returns without error."""
        from config.env_check import check_env

        os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost/test"
        try:
            check_env()  # must not raise
        finally:
            # Restore whatever was there before
            pass
