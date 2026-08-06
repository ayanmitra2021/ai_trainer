"""Admin user management API scenarios — Step 5 (extended).

Scenarios:
  1. Listing admin users returns all accounts ordered by creation date.
  2. Creating a new admin user succeeds and returns must_change_password=True.
  3. Creating an admin user with a duplicate email returns 409.
  4. Creating a user with a too-short password returns 422.
  5. A leadership-role admin cannot create or delete admin users — 403.
  6. An admin cannot delete their own account — 403.
  7. Deleting a non-existent user returns 404.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
import bcrypt as _bcrypt_lib
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AdminUser
from app.db.session import get_db
from app.main import app
from tests.conftest import apply_admin_auth_overrides, apply_leadership_auth_overrides, SessionInfo


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(db_session: AsyncSession, admin_session_info: SessionInfo) -> AsyncClient:
    """HTTP client with full-admin auth overrides."""
    async def _get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_test_db
    apply_admin_auth_overrides(app, admin_session_info)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def leadership_client(
    db_session: AsyncSession, leadership_session_info: SessionInfo
) -> AsyncClient:
    """HTTP client with leadership auth overrides (require_admin NOT bypassed)."""
    async def _get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_test_db
    apply_leadership_auth_overrides(app, leadership_session_info)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def _seed_admin(
    db: AsyncSession,
    email: str = "existing@test.example",
    role: str = "admin",
) -> AdminUser:
    pw_hash = _bcrypt_lib.hashpw(b"temppass1", _bcrypt_lib.gensalt()).decode()
    user = AdminUser(
        id=str(uuid.uuid4()),
        email=email,
        first_name=email.split("@")[0].capitalize(),
        password_hash=pw_hash,
        role=role,
        must_change_password=True,
        created_at=datetime.now(UTC),
    )
    db.add(user)
    await db.flush()
    return user


# ── Scenario tests ─────────────────────────────────────────────────────────────

class TestListAdminUsers:
    async def test_list_returns_all_admin_users(
        self,
        db_session: AsyncSession,
        client: AsyncClient,
    ):
        """
        Scenario: Listing admin users returns all accounts.
          Given two admin users exist in the database
          When GET /admin-users is called
          Then the response contains both users
        """
        # Given
        await _seed_admin(db_session, email="alpha@test.example")
        await _seed_admin(db_session, email="beta@test.example", role="leadership")
        await db_session.flush()

        # When
        resp = await client.get("/api/v1/admin-users")

        # Then
        assert resp.status_code == 200, resp.text
        data = resp.json()
        emails = {u["email"] for u in data}
        assert "alpha@test.example" in emails
        assert "beta@test.example" in emails


class TestCreateAdminUser:
    async def test_create_admin_user_succeeds(
        self,
        db_session: AsyncSession,
        client: AsyncClient,
    ):
        """
        Scenario: Creating a new admin user succeeds with must_change_password=True.
          Given a valid create payload
          When POST /admin-users is called
          Then a 201 is returned with the new user's details
          And must_change_password is True
        """
        # When
        resp = await client.post(
            "/api/v1/admin-users",
            json={
                "email": "newadmin@test.example",
                "first_name": "New",
                "role": "admin",
                "temporary_password": "Temp1234!",
            },
        )

        # Then
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["email"] == "newadmin@test.example"
        assert data["role"] == "admin"
        assert data["must_change_password"] is True
        assert "password" not in data  # hash must never be returned

    async def test_create_leadership_user(
        self,
        db_session: AsyncSession,
        client: AsyncClient,
    ):
        """
        Scenario: Creating a leadership-role account sets role correctly.
          When POST /admin-users is called with role='leadership'
          Then the created user has role='leadership'
        """
        resp = await client.post(
            "/api/v1/admin-users",
            json={
                "email": "leader@test.example",
                "first_name": "Leader",
                "role": "leadership",
                "temporary_password": "Temp1234!",
            },
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["role"] == "leadership"

    async def test_duplicate_email_returns_409(
        self,
        db_session: AsyncSession,
        client: AsyncClient,
    ):
        """
        Scenario: Creating an admin with a duplicate email returns 409.
          Given an admin with email X already exists
          When POST /admin-users is called with the same email
          Then the response is 409
        """
        # Given
        await _seed_admin(db_session, email="dupe@test.example")
        await db_session.flush()

        # When
        resp = await client.post(
            "/api/v1/admin-users",
            json={
                "email": "dupe@test.example",
                "first_name": "Dupe",
                "role": "admin",
                "temporary_password": "Temp1234!",
            },
        )

        # Then
        assert resp.status_code == 409, resp.text

    async def test_short_password_returns_422(
        self,
        db_session: AsyncSession,
        client: AsyncClient,
    ):
        """
        Scenario: A password shorter than 8 characters is rejected.
          When POST /admin-users is called with a 4-char password
          Then the response is 422
        """
        resp = await client.post(
            "/api/v1/admin-users",
            json={
                "email": "shortpw@test.example",
                "first_name": "Short",
                "role": "admin",
                "temporary_password": "abc",
            },
        )
        assert resp.status_code == 422, resp.text


class TestLeadershipCannotManageAdmins:
    async def test_leadership_cannot_create_admin_user(
        self,
        db_session: AsyncSession,
        leadership_client: AsyncClient,
    ):
        """
        Scenario: A leadership-role admin cannot create new admin users.
          Given a leadership session
          When POST /admin-users is called
          Then the response is 403
        """
        resp = await leadership_client.post(
            "/api/v1/admin-users",
            json={
                "email": "blocked@test.example",
                "first_name": "Blocked",
                "role": "admin",
                "temporary_password": "Temp1234!",
            },
        )
        assert resp.status_code == 403, resp.text


class TestDeleteAdminUser:
    async def test_delete_removes_user(
        self,
        db_session: AsyncSession,
        client: AsyncClient,
    ):
        """
        Scenario: Deleting an admin user returns 204 and removes the record.
          Given an admin user exists
          When DELETE /admin-users/{id} is called
          Then the response is 204
          And the user no longer appears in the list
        """
        # Given
        user = await _seed_admin(db_session, email="todelete@test.example")
        await db_session.flush()

        # When
        resp = await client.delete(f"/api/v1/admin-users/{user.id}")

        # Then
        assert resp.status_code == 204, resp.text

        list_resp = await client.get("/api/v1/admin-users")
        emails = {u["email"] for u in list_resp.json()}
        assert "todelete@test.example" not in emails

    async def test_cannot_delete_self(
        self,
        db_session: AsyncSession,
        client: AsyncClient,
        admin_session_info: SessionInfo,
    ):
        """
        Scenario: An admin cannot delete their own account.
          Given the caller's own admin_user_id
          When DELETE /admin-users/{own_id} is called
          Then the response is 403
        """
        resp = await client.delete(
            f"/api/v1/admin-users/{admin_session_info.admin_user_id}"
        )
        assert resp.status_code == 403, resp.text

    async def test_delete_nonexistent_returns_404(
        self,
        db_session: AsyncSession,
        client: AsyncClient,
    ):
        """
        Scenario: Deleting a non-existent admin user returns 404.
        """
        resp = await client.delete(f"/api/v1/admin-users/{uuid.uuid4()}")
        assert resp.status_code == 404, resp.text
