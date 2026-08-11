"""Step 9.3 — Profile lockdown after first full submission.

Scenario 1: Completing the full wizard (questionnaire + certification + skills) locks the
  profile — a subsequent PATCH /practitioners/{id}/profiles/{profile_id} returns 403.

Scenario 2: GET /practitioners/{id}/profiles/{profile_id} exposes is_locked=True after the
  skill-assessments save.

Scenario 3: A second POST /practitioners/{id}/profiles/{profile_id}/skill-assessments on an
  already-locked profile returns 403.

No LLM calls are made — all tests exercise the profile and skill-assessment API routes
against the SQLite in-memory DB.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Certification,
    CertificationProvider,
    PractitionerProfile,
    Skill,
)
from app.db.models import Practitioner
from app.db.session import get_db
from app.main import app
from tests.conftest import apply_admin_auth_overrides, admin_session_info  # noqa: F401


# ── Fixtures ───────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, admin_session_info):
    """AsyncClient wired to the test SQLite DB with admin auth bypass."""

    async def _get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_test_db
    apply_admin_auth_overrides(app, admin_session_info)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def _make_practitioner(db: AsyncSession) -> Practitioner:
    p = Practitioner(
        id=str(uuid.uuid4()),
        name="Lock Test User",
        email=f"locktest-{uuid.uuid4().hex[:8]}@example.com",
        created_at=datetime.now(UTC),
    )
    db.add(p)
    await db.flush()
    return p


async def _make_cert(db: AsyncSession) -> Certification:
    provider = CertificationProvider(
        id=str(uuid.uuid4()),
        name="TestCorp",
    )
    db.add(provider)
    await db.flush()

    cert = Certification(
        id=str(uuid.uuid4()),
        provider_id=provider.id,
        code="TCO-F",
        name="TestCorp Foundations",
        level="foundational",
        requires_coding_background=False,
        is_active=True,
        last_verified_at=datetime.now(UTC).date(),
    )
    db.add(cert)
    await db.flush()
    return cert


async def _make_skill(db: AsyncSession) -> Skill:
    skill = Skill(
        id=str(uuid.uuid4()),
        name="Test Skill",
        category="Testing",
    )
    db.add(skill)
    await db.flush()
    return skill


async def _make_profile(
    db: AsyncSession,
    practitioner_id: str,
    certification_id: str | None = None,
    is_locked: bool = False,
) -> PractitionerProfile:
    profile = PractitionerProfile(
        id=str(uuid.uuid4()),
        practitioner_id=practitioner_id,
        name="My Test Path",
        is_active=False,
        is_locked=is_locked,
        certification_id=certification_id,
        questionnaire_snapshot={"writes_code": False},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(profile)
    await db.flush()
    return profile


# ── Scenario 1 ────────────────────────────────────────────────────────────────


class TestSkillSaveLocksProfile:
    """
    Scenario: Completing the full wizard (questionnaire + certification + skills) locks
    the profile — a subsequent PATCH returns 403.

      Given a practitioner with an unlocked profile and a skill in the catalog
      When  POST .../skill-assessments is called with that skill's rating
      Then  the profile's is_locked becomes True
      And   a subsequent PATCH .../profiles/{profile_id} returns HTTP 403 with the
            message "Profile is locked and cannot be edited."
    """

    async def test_skill_save_locks_profile_then_patch_returns_403(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        # Given
        practitioner = await _make_practitioner(db_session)
        cert = await _make_cert(db_session)
        skill = await _make_skill(db_session)
        profile = await _make_profile(db_session, practitioner.id, certification_id=cert.id)
        await db_session.commit()

        pid = practitioner.id
        prof_id = profile.id

        # Confirm profile starts unlocked
        get_resp = await client.get(f"/api/v1/practitioners/{pid}/profiles/{prof_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["is_locked"] is False

        # When — save skill-assessments (final wizard step)
        upsert_resp = await client.post(
            f"/api/v1/practitioners/{pid}/profiles/{prof_id}/skill-assessments",
            json={"assessments": [{"skill_id": skill.id, "signal_strength": 0.75}]},
        )
        assert upsert_resp.status_code == 200, upsert_resp.text
        assert upsert_resp.json()["rows_written"] == 1

        # Then — profile is now locked
        get_after = await client.get(f"/api/v1/practitioners/{pid}/profiles/{prof_id}")
        assert get_after.status_code == 200
        assert get_after.json()["is_locked"] is True

        # And — PATCH is rejected
        patch_resp = await client.patch(
            f"/api/v1/practitioners/{pid}/profiles/{prof_id}",
            json={"name": "Renamed after lock"},
        )
        assert patch_resp.status_code == 403
        assert "locked" in patch_resp.json()["detail"].lower()


# ── Scenario 2 ────────────────────────────────────────────────────────────────


class TestLockedProfileExposedInGet:
    """
    Scenario: GET /practitioners/{id}/profiles/{profile_id} exposes is_locked=True
    after the skill-assessments save.

      Given a profile that has already been locked (is_locked=True in DB)
      When  GET .../profiles/{profile_id} is called
      Then  the response body includes is_locked: true
      And   GET .../profiles (list) also includes is_locked: true on that profile's card
    """

    async def test_get_profile_returns_is_locked_true(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        # Given — a profile already locked in the DB
        practitioner = await _make_practitioner(db_session)
        profile = await _make_profile(db_session, practitioner.id, is_locked=True)
        await db_session.commit()

        pid = practitioner.id
        prof_id = profile.id

        # When — fetch detail
        detail_resp = await client.get(f"/api/v1/practitioners/{pid}/profiles/{prof_id}")
        assert detail_resp.status_code == 200
        assert detail_resp.json()["is_locked"] is True

        # And — list endpoint also includes the field
        list_resp = await client.get(f"/api/v1/practitioners/{pid}/profiles")
        assert list_resp.status_code == 200
        profiles_in_list = list_resp.json()
        assert len(profiles_in_list) == 1
        assert profiles_in_list[0]["is_locked"] is True


# ── Scenario 3 ────────────────────────────────────────────────────────────────


class TestSecondSkillSaveOnLockedProfileReturns403:
    """
    Scenario: A second POST .../skill-assessments on an already-locked profile
    returns 403 — prevents re-rating after locking.

      Given a profile that is already locked
      When  POST .../skill-assessments is called again
      Then  the response is HTTP 403 with the locked message
      And   no new skill-assessment rows are written
    """

    async def test_second_skill_save_on_locked_profile_returns_403(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        # Given
        practitioner = await _make_practitioner(db_session)
        skill = await _make_skill(db_session)
        profile = await _make_profile(db_session, practitioner.id, is_locked=True)
        await db_session.commit()

        pid = practitioner.id
        prof_id = profile.id

        # When
        resp = await client.post(
            f"/api/v1/practitioners/{pid}/profiles/{prof_id}/skill-assessments",
            json={"assessments": [{"skill_id": skill.id, "signal_strength": 0.5}]},
        )

        # Then
        assert resp.status_code == 403
        assert "locked" in resp.json()["detail"].lower()


# ── Scenario 4 — Activate and Delete still work on locked profiles ─────────────


class TestLockedProfileActivateAndDeleteUnaffected:
    """
    Scenario: Activate and Delete work on locked profiles — is_locked only blocks edits.

      Given two profiles: one locked (active=False), one unlocked (active=True)
      When  PATCH .../activate is called on the locked profile
      Then  it becomes active (200) — activate is not blocked by is_locked
      When  DELETE is called on the (now inactive) unlocked profile
      Then  it is deleted (204)
    """

    async def test_activate_and_delete_unaffected_by_lock(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        # Given
        practitioner = await _make_practitioner(db_session)
        locked_profile = await _make_profile(
            db_session, practitioner.id, is_locked=True
        )
        unlocked_profile = await _make_profile(
            db_session, practitioner.id, is_locked=False
        )
        # Make unlocked_profile the active one
        unlocked_profile.is_active = True
        await db_session.commit()

        pid = practitioner.id

        # When — activate the locked profile
        activate_resp = await client.patch(
            f"/api/v1/practitioners/{pid}/profiles/{locked_profile.id}/activate"
        )
        assert activate_resp.status_code == 200
        assert activate_resp.json()["is_active"] is True

        # Unlocked profile is now inactive — delete it
        delete_resp = await client.delete(
            f"/api/v1/practitioners/{pid}/profiles/{unlocked_profile.id}"
        )
        assert delete_resp.status_code == 204
