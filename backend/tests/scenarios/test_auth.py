"""Step 5.2 — Auth & access control scenarios.

Scenarios:
  1. A practitioner logs in by email and is routed directly to their own data.
  2. Relaunching the app and re-entering the same email restores learning history.
  3. A practitioner cannot fetch another practitioner's individual profile — 403.
  4. A leadership-role admin can view rollups and nudges but not individual attempts — 403.
  5. An admin with must_change_password=True is blocked from data views.
  6. An admin cannot log in with the wrong password — 401.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import bcrypt as _bcrypt_lib
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AdminUser, Attempt, Item, Nudge, Practitioner
from app.db.models import Session as SessionModel
from app.db.session import get_db
from app.main import app


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def auth_client(db_session: AsyncSession) -> AsyncClient:
    """Unauthenticated client — auth is tested by cookies, not overrides."""
    async def _get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_test_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def _create_practitioner(db: AsyncSession, name: str, email: str) -> Practitioner:
    p = Practitioner(id=str(uuid.uuid4()), name=name, email=email)
    db.add(p)
    await db.flush()
    return p


async def _create_admin(
    db: AsyncSession,
    email: str,
    password: str,
    role: str = "admin",
    must_change_password: bool = False,
) -> AdminUser:
    admin = AdminUser(
        id=str(uuid.uuid4()),
        email=email,
        first_name=email.split("@")[0].capitalize(),
        password_hash=_bcrypt_lib.hashpw(password.encode(), _bcrypt_lib.gensalt()).decode(),
        role=role,
        must_change_password=must_change_password,
    )
    db.add(admin)
    await db.flush()
    return admin


async def _create_session(
    db: AsyncSession,
    *,
    identity_type: str,
    practitioner_id: str | None = None,
    admin_user_id: str | None = None,
    expires_at: datetime | None = None,
) -> SessionModel:
    session = SessionModel(
        id=str(uuid.uuid4()),
        identity_type=identity_type,
        practitioner_id=practitioner_id,
        admin_user_id=admin_user_id,
        expires_at=expires_at,
    )
    db.add(session)
    await db.flush()
    return session


# ── Scenario tests ─────────────────────────────────────────────────────────────

class TestPractitionerLoginFlow:
    async def test_login_creates_session_and_returns_identity(
        self,
        db_session: AsyncSession,
        auth_client: AsyncClient,
    ):
        """
        Scenario: A practitioner logs in by email and gets back their identity.
          Given a valid name/email/org_level payload
          When POST /auth/practitioner-login is called
          Then the response contains identity_type='practitioner' and a practitioner_id
          And a session cookie is set
        """
        # When
        resp = await auth_client.post(
            "/api/v1/auth/practitioner-login",
            json={"name": "Alex Rivera", "email": "alex.auth.test@example.com", "org_level": "Senior"},
        )

        # Then
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["identity_type"] == "practitioner"
        assert data["first_name"] == "Alex"
        assert "practitioner_id" in data
        assert resp.cookies.get("mastery_session") is not None

    async def test_relogin_same_email_restores_learning_history(
        self,
        db_session: AsyncSession,
        auth_client: AsyncClient,
    ):
        """
        Scenario: Relaunching the app and re-entering the same email restores data.
          Given a practitioner that already exists in the DB
          When POST /auth/practitioner-login is called with the same email
          Then the response returns the SAME practitioner_id (not a new one)
        """
        # Given — first login creates the practitioner
        resp1 = await auth_client.post(
            "/api/v1/auth/practitioner-login",
            json={"name": "Jordan Kim", "email": "jordan.relogin@example.com"},
        )
        assert resp1.status_code == 200
        original_id = resp1.json()["practitioner_id"]

        # When — second login with same email
        resp2 = await auth_client.post(
            "/api/v1/auth/practitioner-login",
            json={"name": "Jordan Kim", "email": "jordan.relogin@example.com"},
        )

        # Then — same practitioner_id
        assert resp2.status_code == 200
        assert resp2.json()["practitioner_id"] == original_id


class TestPractitionerSelfEnforcement:
    async def test_practitioner_cannot_fetch_another_practitioner_profile(
        self,
        db_session: AsyncSession,
        auth_client: AsyncClient,
    ):
        """
        Scenario: A practitioner cannot fetch another practitioner's individual profile.
          Given practitioner A is logged in
          When GET /practitioners/{id_of_practitioner_B}/skill-profile is called
          Then the response is 403
        """
        # Given — create two practitioners
        p_a = await _create_practitioner(db_session, "Practitioner A", "p.a@test.example")
        p_b = await _create_practitioner(db_session, "Practitioner B", "p.b@test.example")
        session_a = await _create_session(
            db_session,
            identity_type="practitioner",
            practitioner_id=p_a.id,
            expires_at=None,
        )
        await db_session.flush()

        # When — use session_a's cookie to request p_b's profile
        resp = await auth_client.get(
            f"/api/v1/practitioners/{p_b.id}/skill-profile",
            cookies={"mastery_session": session_a.id},
        )

        # Then
        assert resp.status_code == 403, (
            f"Expected 403, got {resp.status_code}: {resp.text}"
        )


class TestLeadershipAdminAccess:
    async def test_leadership_cannot_access_individual_attempts(
        self,
        db_session: AsyncSession,
        auth_client: AsyncClient,
    ):
        """
        Scenario: A leadership-role admin can view rollups but not individual attempts.
          Given a leadership admin session
          And an attempt row in the DB
          When GET /attempts/{id} is called with the leadership session
          Then the response is 403
        """
        # Given — create a practitioner, an item, and an attempt
        p = await _create_practitioner(db_session, "Casey Test", "casey.test@test.example")
        skill_id = str(uuid.uuid4())

        from app.db.models import Skill
        skill = Skill(id=skill_id, name="Test Skill", category="Test")
        db_session.add(skill)
        await db_session.flush()

        item = Item(
            id=str(uuid.uuid4()),
            skill_id=skill_id,
            item_type="mcq",
            prompt="What is 2+2?",
            answer_key={"options": ["3", "4", "5"], "correct_index": 1},
            trap_explanation=None,
            difficulty=0.3,
        )
        db_session.add(item)
        attempt = Attempt(
            id=str(uuid.uuid4()),
            practitioner_id=p.id,
            item_id=item.id,
            response={"selected_index": 1},
            score=1.0,
            grader_rationale="Correct.",
            is_trap_selected=False,
            attempted_at=datetime.now(UTC),
        )
        db_session.add(attempt)
        await db_session.flush()

        # Create a leadership admin and session
        leadership = await _create_admin(
            db_session, "leader@test.example", "pass123", role="leadership"
        )
        l_session = await _create_session(
            db_session,
            identity_type="admin",
            admin_user_id=leadership.id,
            expires_at=datetime.now(UTC) + timedelta(hours=8),
        )
        await db_session.flush()

        # When
        resp = await auth_client.get(
            f"/api/v1/attempts/{attempt.id}",
            cookies={"mastery_session": l_session.id},
        )

        # Then — leadership sees aggregates, not individual attempts
        assert resp.status_code == 403, (
            f"Expected 403 for leadership accessing individual attempt, got {resp.status_code}"
        )

    async def test_leadership_rollups_endpoint_returns_404_phase91(
        self,
        db_session: AsyncSession,
        auth_client: AsyncClient,
    ):
        """
        Scenario (Phase 9.1): GET /rollups returns 404 — rollups removed.
          Given a leadership session
          When GET /rollups is called
          Then 404 is returned (the endpoint no longer exists)

        Replaces the pre-Phase-9.1 test that checked for 200 — rollups are gone.
        """
        # Given
        now = datetime.now(UTC)
        leadership = await _create_admin(
            db_session, "leader2@test.example", "pass123", role="leadership"
        )
        l_session = await _create_session(
            db_session,
            identity_type="admin",
            admin_user_id=leadership.id,
            expires_at=now + timedelta(hours=8),
        )
        await db_session.flush()

        # When
        resp = await auth_client.get(
            "/api/v1/rollups",
            cookies={"mastery_session": l_session.id},
        )

        # Then — 404, not 200 (rollups removed in Phase 9.1)
        assert resp.status_code == 404, (
            f"Expected 404 for /rollups after Phase 9.1 removal, got {resp.status_code}. "
            f"Body: {resp.text}"
        )


class TestAdminPasswordEnforcement:
    async def test_admin_with_must_change_password_blocked_from_data(
        self,
        db_session: AsyncSession,
        auth_client: AsyncClient,
    ):
        """
        Scenario: An admin with must_change_password=True cannot access data views.
          Given an admin with must_change_password=True and an active session
          When GET /observability/agent-runs is called
          Then the response is 403
        """
        # Given
        admin = await _create_admin(
            db_session,
            "newadmin@test.example",
            "welcome",
            must_change_password=True,
        )
        session = await _create_session(
            db_session,
            identity_type="admin",
            admin_user_id=admin.id,
            expires_at=datetime.now(UTC) + timedelta(hours=8),
        )
        await db_session.flush()

        # When
        resp = await auth_client.get(
            "/api/v1/observability/agent-runs",
            cookies={"mastery_session": session.id},
        )

        # Then
        assert resp.status_code == 403
        assert "password" in resp.json()["detail"].lower()

    async def test_admin_wrong_password_returns_401(
        self,
        db_session: AsyncSession,
        auth_client: AsyncClient,
    ):
        """
        Scenario: An admin cannot log in with the wrong password.
          Given an admin account with a known bcrypt password
          When POST /auth/admin-login is called with the wrong password
          Then the response is 401
        """
        # Given
        await _create_admin(
            db_session, "admin.pw@test.example", "correctpassword"
        )
        await db_session.flush()

        # When
        resp = await auth_client.post(
            "/api/v1/auth/admin-login",
            json={"email": "admin.pw@test.example", "password": "wrongpassword"},
        )

        # Then
        assert resp.status_code == 401
        assert "invalid" in resp.json()["detail"].lower()

    async def test_change_password_clears_must_change_flag(
        self,
        db_session: AsyncSession,
        auth_client: AsyncClient,
    ):
        """
        Scenario: After changing password must_change_password becomes False.
          Given an admin with must_change_password=True and a valid session
          When POST /auth/change-password is called with the correct current password
          Then the response is 204
          And GET /auth/me no longer reports must_change_password=True
        """
        # Given
        admin = await _create_admin(
            db_session, "changepw@test.example", "welcome", must_change_password=True
        )
        session = await _create_session(
            db_session,
            identity_type="admin",
            admin_user_id=admin.id,
            expires_at=datetime.now(UTC) + timedelta(hours=8),
        )
        await db_session.flush()

        # When
        resp = await auth_client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "welcome", "new_password": "newSecure123!"},
            cookies={"mastery_session": session.id},
        )

        # Then
        assert resp.status_code == 204, resp.text

        # Refresh DB state
        await db_session.refresh(admin)
        assert admin.must_change_password is False
