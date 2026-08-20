"""Phase 22 — Multi-Tenant SaaS scenarios.

Covers Steps 22.1–22.6 (DB schema, product-admin auth, subscription plans,
organizations, enrollment/registration, and plan enforcement).

All tests run against in-memory SQLite via the ``db_session`` + ``auth_client``
fixtures. Where Postgres-specific behavior (partial unique indexes) is tested,
the API-layer enforcement is validated rather than the DDL.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import bcrypt as _bcrypt_lib
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AdminUser,
    OrgEnrollmentCode,
    Organization,
    Practitioner,
    PractitionerProfile,
    ProductAdminUser,
    Session as SessionModel,
    SubscriptionPlan,
)
from app.db.session import get_db
from app.main import app


# ── Shared fixtures ────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def mt_client(db_session: AsyncSession) -> AsyncClient:
    """Unauthenticated client backed by the in-memory SQLite session."""

    async def _get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_test_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# ── Factory helpers ────────────────────────────────────────────────────────────

def _hash(password: str) -> str:
    return _bcrypt_lib.hashpw(password.encode(), _bcrypt_lib.gensalt()).decode()


async def _create_plan(
    db: AsyncSession,
    *,
    name: str = "Test Free",
    tier: str = "free",
    max_profiles: int = 2,
    max_paths: int = 2,
    max_exams: int = 2,
    max_practitioners: int = -1,
    allow_recycling: bool = False,
    nudges_enabled: bool = False,
    teams_enabled: bool = False,
) -> SubscriptionPlan:
    now = datetime.now(UTC)
    plan = SubscriptionPlan(
        id=str(uuid.uuid4()),
        name=name,
        tier=tier,
        max_profiles_per_practitioner=max_profiles,
        max_learning_paths=max_paths,
        max_mock_exams_per_profile=max_exams,
        max_practitioners_per_org=max_practitioners,
        allow_cert_recycling=allow_recycling,
        nudges_enabled=nudges_enabled,
        teams_notifications_enabled=teams_enabled,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db.add(plan)
    await db.flush()
    return plan


async def _create_org(
    db: AsyncSession,
    *,
    name: str = "Test Org",
    plan_id: str,
    is_active: bool = True,
) -> Organization:
    now = datetime.now(UTC)
    org = Organization(
        id=str(uuid.uuid4()),
        name=name,
        plan_id=plan_id,
        billing_email=None,
        is_active=is_active,
        created_at=now,
        updated_at=now,
    )
    db.add(org)
    await db.flush()
    return org


async def _create_code(
    db: AsyncSession, *, org_id: str, code: str = "ABCD1234EFGH5678", is_active: bool = True
) -> OrgEnrollmentCode:
    ec = OrgEnrollmentCode(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        code=code,
        is_active=is_active,
        created_at=datetime.now(UTC),
    )
    db.add(ec)
    await db.flush()
    return ec


async def _create_product_admin(
    db: AsyncSession,
    *,
    email: str = "padmin@test.example",
    password: str = "Welcome1!",
    must_change_password: bool = False,
) -> ProductAdminUser:
    pa = ProductAdminUser(
        id=str(uuid.uuid4()),
        email=email,
        password_hash=_hash(password),
        first_name="Platform",
        must_change_password=must_change_password,
        created_at=datetime.now(UTC),
    )
    db.add(pa)
    await db.flush()
    return pa


async def _create_practitioner(
    db: AsyncSession,
    *,
    name: str = "Test User",
    email: str | None = None,
    org_id: str | None = None,
    is_active: bool = True,
) -> Practitioner:
    if email is None:
        email = f"user.{uuid.uuid4().hex[:8]}@test.example"
    p = Practitioner(
        id=str(uuid.uuid4()),
        name=name,
        email=email,
        organization_id=org_id,
        is_active=is_active,
        created_at=datetime.now(UTC),
    )
    db.add(p)
    await db.flush()
    return p


async def _create_product_admin_session(
    db: AsyncSession, product_admin_id: str
) -> SessionModel:
    now = datetime.now(UTC)
    sess = SessionModel(
        id=str(uuid.uuid4()),
        identity_type="product_admin",
        practitioner_id=None,
        admin_user_id=None,
        product_admin_user_id=product_admin_id,
        expires_at=now + timedelta(hours=8),
        created_at=now,
        last_seen_at=now,
    )
    db.add(sess)
    await db.flush()
    return sess


async def _create_prac_session(db: AsyncSession, practitioner_id: str) -> SessionModel:
    now = datetime.now(UTC)
    sess = SessionModel(
        id=str(uuid.uuid4()),
        identity_type="practitioner",
        practitioner_id=practitioner_id,
        admin_user_id=None,
        product_admin_user_id=None,
        expires_at=None,
        created_at=now,
        last_seen_at=now,
    )
    db.add(sess)
    await db.flush()
    return sess


async def _create_admin_user(
    db: AsyncSession, *, email: str, org_id: str | None = None
) -> AdminUser:
    admin = AdminUser(
        id=str(uuid.uuid4()),
        email=email,
        first_name="Admin",
        password_hash=_hash("password"),
        role="admin",
        must_change_password=False,
        organization_id=org_id,
        created_at=datetime.now(UTC),
    )
    db.add(admin)
    await db.flush()
    return admin


async def _create_admin_session(db: AsyncSession, admin_id: str) -> SessionModel:
    now = datetime.now(UTC)
    sess = SessionModel(
        id=str(uuid.uuid4()),
        identity_type="admin",
        practitioner_id=None,
        admin_user_id=admin_id,
        product_admin_user_id=None,
        expires_at=now + timedelta(hours=8),
        created_at=now,
        last_seen_at=now,
    )
    db.add(sess)
    await db.flush()
    return sess


# ══════════════════════════════════════════════════════════════════════════════
# Step 22.1 — DB schema scenarios
# ══════════════════════════════════════════════════════════════════════════════

class TestStep221DBSchema:
    async def test_org_with_valid_plan_can_be_created_and_fetched(
        self,
        db_session: AsyncSession,
        mt_client: AsyncClient,
    ) -> None:
        """
        Scenario: A new organization row referencing a valid plan can be created and fetched.
          Given a SubscriptionPlan exists
          When an Organization is inserted with plan_id pointing to that plan
          Then the organization can be fetched and its plan relationship resolves
        """
        plan = await _create_plan(db_session, name="Enterprise", tier="enterprise", nudges_enabled=True)
        org = await _create_org(db_session, name="ACME Corp", plan_id=plan.id)
        await db_session.flush()

        result = await db_session.execute(
            select(Organization).where(Organization.id == org.id)
        )
        fetched = result.scalar_one()
        assert fetched.name == "ACME Corp"
        assert fetched.plan_id == plan.id
        assert fetched.is_active is True

    async def test_two_active_codes_for_same_org_rejected_by_api(
        self,
        db_session: AsyncSession,
        mt_client: AsyncClient,
    ) -> None:
        """
        Scenario: Two active codes for the same org are rejected (API enforces uniqueness).
          Given a product admin session and an org with an active code
          When POST /product-admin/organizations/{id}/regenerate-code is called
          Then the old code is deactivated and a new one is returned (only one active at a time)

        Note: partial unique indexes may not enforce in SQLite; we verify API behavior.
        """
        pa = await _create_product_admin(db_session)
        pa_sess = await _create_product_admin_session(db_session, pa.id)

        plan = await _create_plan(db_session, tier="enterprise", nudges_enabled=True)
        org = await _create_org(db_session, plan_id=plan.id)
        old_code = await _create_code(db_session, org_id=org.id, code="AAAA1111BBBB2222")
        await db_session.flush()

        resp = await mt_client.post(
            f"/api/v1/product-admin/organizations/{org.id}/regenerate-code",
            cookies={"mastery_session": pa_sess.id},
        )
        assert resp.status_code == 200, resp.text
        new_code_value = resp.json()["code"]
        assert len(new_code_value) == 16
        assert new_code_value != "AAAA1111BBBB2222"

        # Old code should now be inactive
        await db_session.refresh(old_code)
        assert old_code.is_active is False

        # Count active codes: should be exactly 1
        result = await db_session.execute(
            select(OrgEnrollmentCode).where(
                OrgEnrollmentCode.organization_id == org.id,
                OrgEnrollmentCode.is_active.is_(True),
            )
        )
        active_codes = result.scalars().all()
        assert len(active_codes) == 1

    async def test_soft_deleted_profile_excluded_from_normal_list(
        self,
        db_session: AsyncSession,
        mt_client: AsyncClient,
    ) -> None:
        """
        Scenario: A profile with deleted_at IS NOT NULL is excluded from GET .../profiles responses.
          Given a practitioner with two profiles, one soft-deleted
          When GET /practitioners/{id}/profiles is called
          Then only the non-deleted profile is returned
        """
        plan = await _create_plan(db_session, tier="free")
        org = await _create_org(db_session, plan_id=plan.id)
        prac = await _create_practitioner(db_session, org_id=org.id)
        prac_sess = await _create_prac_session(db_session, prac.id)

        now = datetime.now(UTC)
        active_profile = PractitionerProfile(
            id=str(uuid.uuid4()),
            practitioner_id=prac.id,
            name="Active Profile",
            is_active=True,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )
        deleted_profile = PractitionerProfile(
            id=str(uuid.uuid4()),
            practitioner_id=prac.id,
            name="Deleted Profile",
            is_active=False,
            created_at=now,
            updated_at=now,
            deleted_at=now,
        )
        db_session.add(active_profile)
        db_session.add(deleted_profile)
        await db_session.flush()

        resp = await mt_client.get(
            f"/api/v1/practitioners/{prac.id}/profiles",
            cookies={"mastery_session": prac_sess.id},
        )
        assert resp.status_code == 200, resp.text
        profiles = resp.json()
        profile_ids = {p["id"] for p in profiles}
        assert active_profile.id in profile_ids
        assert deleted_profile.id not in profile_ids


# ══════════════════════════════════════════════════════════════════════════════
# Step 22.2 — Product Admin auth scenarios
# ══════════════════════════════════════════════════════════════════════════════

class TestStep222ProductAdminAuth:
    async def test_valid_credentials_create_product_admin_session(
        self,
        db_session: AsyncSession,
        mt_client: AsyncClient,
    ) -> None:
        """
        Scenario: Valid product admin credentials → session with identity_type=product_admin.
          Given a ProductAdminUser row
          When POST /product-admin/login is called with correct credentials
          Then the response is 200 with identity_type=product_admin
          And a session cookie is set
        """
        pa = await _create_product_admin(db_session, email="pa1@test.example", password="Welcome1!")
        await db_session.flush()

        resp = await mt_client.post(
            "/api/v1/product-admin/login",
            json={"email": "pa1@test.example", "password": "Welcome1!"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["identity_type"] == "product_admin"
        assert data["first_name"] == "Platform"
        assert resp.cookies.get("mastery_session") is not None

    async def test_invalid_credentials_return_401(
        self,
        db_session: AsyncSession,
        mt_client: AsyncClient,
    ) -> None:
        """
        Scenario: Invalid credentials → 401.
          Given a ProductAdminUser row
          When POST /product-admin/login is called with wrong password
          Then the response is 401
        """
        await _create_product_admin(db_session, email="pa2@test.example", password="correct")
        await db_session.flush()

        resp = await mt_client.post(
            "/api/v1/product-admin/login",
            json={"email": "pa2@test.example", "password": "wrong"},
        )
        assert resp.status_code == 401

    async def test_require_product_admin_rejects_org_admin(
        self,
        db_session: AsyncSession,
        mt_client: AsyncClient,
    ) -> None:
        """
        Scenario: require_product_admin rejects org-admin sessions with 403.
          Given an org admin session
          When GET /product-admin/me is called
          Then the response is 403
        """
        admin = await _create_admin_user(db_session, email="orgadmin@test.example")
        admin_sess = await _create_admin_session(db_session, admin.id)
        await db_session.flush()

        resp = await mt_client.get(
            "/api/v1/product-admin/me",
            cookies={"mastery_session": admin_sess.id},
        )
        assert resp.status_code == 403

    async def test_require_product_admin_rejects_practitioner(
        self,
        db_session: AsyncSession,
        mt_client: AsyncClient,
    ) -> None:
        """
        Scenario: require_product_admin rejects practitioner sessions with 403.
          Given a practitioner session
          When GET /product-admin/me is called
          Then the response is 403
        """
        prac = await _create_practitioner(db_session)
        prac_sess = await _create_prac_session(db_session, prac.id)
        await db_session.flush()

        resp = await mt_client.get(
            "/api/v1/product-admin/me",
            cookies={"mastery_session": prac_sess.id},
        )
        assert resp.status_code == 403


# ══════════════════════════════════════════════════════════════════════════════
# Step 22.3 — Subscription plan management scenarios
# ══════════════════════════════════════════════════════════════════════════════

class TestStep223PlanManagement:
    async def test_create_valid_paid_plan(
        self,
        db_session: AsyncSession,
        mt_client: AsyncClient,
    ) -> None:
        """
        Scenario: Create a valid Paid plan → returned plan matches input.
          Given a product admin session
          When POST /product-admin/plans is called with valid paid plan data
          Then the response is 201 and the plan data matches
        """
        pa = await _create_product_admin(db_session, email="pa3@test.example")
        pa_sess = await _create_product_admin_session(db_session, pa.id)
        await db_session.flush()

        resp = await mt_client.post(
            "/api/v1/product-admin/plans",
            json={
                "name": "Paid Pro",
                "tier": "paid",
                "max_profiles_per_practitioner": 5,
                "max_learning_paths": 10,
                "max_mock_exams_per_profile": 10,
                "max_practitioners_per_org": -1,
                "allow_cert_recycling": True,
                "nudges_enabled": False,
                "teams_notifications_enabled": False,
            },
            cookies={"mastery_session": pa_sess.id},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["name"] == "Paid Pro"
        assert data["tier"] == "paid"
        assert data["max_profiles_per_practitioner"] == 5
        assert data["allow_cert_recycling"] is True

    async def test_create_plan_with_zero_limit_returns_422(
        self,
        db_session: AsyncSession,
        mt_client: AsyncClient,
    ) -> None:
        """
        Scenario: Attempt to set max_profiles_per_practitioner=0 → 422.
          Given a product admin session
          When POST /product-admin/plans is called with limit=0
          Then the response is 422
        """
        pa = await _create_product_admin(db_session, email="pa4@test.example")
        pa_sess = await _create_product_admin_session(db_session, pa.id)
        await db_session.flush()

        resp = await mt_client.post(
            "/api/v1/product-admin/plans",
            json={
                "name": "Bad Plan",
                "tier": "paid",
                "max_profiles_per_practitioner": 0,
                "max_learning_paths": 2,
                "max_mock_exams_per_profile": 2,
                "max_practitioners_per_org": -1,
            },
            cookies={"mastery_session": pa_sess.id},
        )
        assert resp.status_code == 422

    async def test_deactivate_plan_with_no_active_orgs(
        self,
        db_session: AsyncSession,
        mt_client: AsyncClient,
    ) -> None:
        """
        Scenario: Deactivate a plan with no active orgs → 200.
          Given a product admin session and a plan with no active organizations
          When DELETE /product-admin/plans/{id} is called
          Then the response is 200
        """
        pa = await _create_product_admin(db_session, email="pa5@test.example")
        pa_sess = await _create_product_admin_session(db_session, pa.id)
        plan = await _create_plan(db_session, name="Unused Plan", tier="paid")
        await db_session.flush()

        resp = await mt_client.delete(
            f"/api/v1/product-admin/plans/{plan.id}",
            cookies={"mastery_session": pa_sess.id},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["deactivated"] is True

    async def test_deactivate_plan_with_active_orgs_returns_409(
        self,
        db_session: AsyncSession,
        mt_client: AsyncClient,
    ) -> None:
        """
        Scenario: Deactivate a plan with 3 active orgs → 409 with active_org_count: 3.
          Given a product admin session and a plan with 3 active orgs
          When DELETE /product-admin/plans/{id} is called
          Then the response is 409 with active_org_count=3
        """
        pa = await _create_product_admin(db_session, email="pa6@test.example")
        pa_sess = await _create_product_admin_session(db_session, pa.id)
        plan = await _create_plan(db_session, name="Busy Plan", tier="paid")
        for i in range(3):
            await _create_org(db_session, name=f"Org {i}", plan_id=plan.id)
        await db_session.flush()

        resp = await mt_client.delete(
            f"/api/v1/product-admin/plans/{plan.id}",
            cookies={"mastery_session": pa_sess.id},
        )
        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert detail["active_org_count"] == 3


# ══════════════════════════════════════════════════════════════════════════════
# Step 22.4 — Organization management scenarios
# ══════════════════════════════════════════════════════════════════════════════

class TestStep224OrgManagement:
    async def test_creating_org_generates_one_16char_code(
        self,
        db_session: AsyncSession,
        mt_client: AsyncClient,
    ) -> None:
        """
        Scenario: Creating an org generates exactly one 16-char uppercase alphanumeric code.
          Given a product admin session and a plan
          When POST /product-admin/organizations is called
          Then the org has exactly one active enrollment code of length 16
        """
        pa = await _create_product_admin(db_session, email="pa7@test.example")
        pa_sess = await _create_product_admin_session(db_session, pa.id)
        plan = await _create_plan(db_session, tier="enterprise", nudges_enabled=True)
        await db_session.flush()

        resp = await mt_client.post(
            "/api/v1/product-admin/organizations",
            json={"name": "Code Test Org", "plan_id": plan.id},
            cookies={"mastery_session": pa_sess.id},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        code = data["enrollment_code"]
        assert code is not None
        assert len(code) == 16
        assert code == code.upper()

    async def test_regenerate_code_deactivates_old_returns_new(
        self,
        db_session: AsyncSession,
        mt_client: AsyncClient,
    ) -> None:
        """
        Scenario: Regenerating a code deactivates the old code and returns a new one.
          Given an org with an active code
          When POST /product-admin/organizations/{id}/regenerate-code is called
          Then a new code is returned and the old one is inactive
        """
        pa = await _create_product_admin(db_session, email="pa8@test.example")
        pa_sess = await _create_product_admin_session(db_session, pa.id)
        plan = await _create_plan(db_session, tier="enterprise", nudges_enabled=True)
        org = await _create_org(db_session, plan_id=plan.id)
        old_code = await _create_code(db_session, org_id=org.id, code="ZZZZ9999AAAA1111")
        await db_session.flush()

        resp = await mt_client.post(
            f"/api/v1/product-admin/organizations/{org.id}/regenerate-code",
            cookies={"mastery_session": pa_sess.id},
        )
        assert resp.status_code == 200, resp.text
        new_code = resp.json()["code"]
        assert new_code != "ZZZZ9999AAAA1111"
        assert len(new_code) == 16

        await db_session.refresh(old_code)
        assert old_code.is_active is False

    async def test_deactivating_enterprise_org_returns_enterprise_message(
        self,
        db_session: AsyncSession,
        mt_client: AsyncClient,
    ) -> None:
        """
        Scenario: Deactivating an enterprise org → practitioner login returns 403
                  with 'enterprise administrator' in the message.
          Given a practitioner in an enterprise org
          When the org is deactivated and the practitioner tries to log in
          Then the response is 403 with tier-specific enterprise message
        """
        pa = await _create_product_admin(db_session, email="pa9@test.example")
        pa_sess = await _create_product_admin_session(db_session, pa.id)
        plan = await _create_plan(db_session, tier="enterprise", nudges_enabled=True)
        org = await _create_org(db_session, name="Enterprise Org", plan_id=plan.id)
        prac = await _create_practitioner(
            db_session, email="entprac@test.example", org_id=org.id
        )
        await db_session.flush()

        # Deactivate org
        deact_resp = await mt_client.patch(
            f"/api/v1/product-admin/organizations/{org.id}/deactivate",
            cookies={"mastery_session": pa_sess.id},
        )
        assert deact_resp.status_code == 200

        # Practitioner attempts login
        login_resp = await mt_client.post(
            "/api/v1/auth/practitioner-login",
            json={"name": "Ent Prac", "email": "entprac@test.example"},
        )
        assert login_resp.status_code == 403
        detail = login_resp.json()["detail"]
        assert detail["error"] == "org_suspended"
        assert "enterprise administrator" in detail["message"]

    async def test_deactivating_free_plan_org_returns_plan_message(
        self,
        db_session: AsyncSession,
        mt_client: AsyncClient,
    ) -> None:
        """
        Scenario: Deactivating a free plan org → practitioner login returns 403
                  with 'plan administrator' in the message.
        """
        pa = await _create_product_admin(db_session, email="pa10@test.example")
        pa_sess = await _create_product_admin_session(db_session, pa.id)
        plan = await _create_plan(db_session, tier="free")
        org = await _create_org(db_session, name="Free Org", plan_id=plan.id)
        prac = await _create_practitioner(
            db_session, email="freeprac@test.example", org_id=org.id
        )
        await db_session.flush()

        deact_resp = await mt_client.patch(
            f"/api/v1/product-admin/organizations/{org.id}/deactivate",
            cookies={"mastery_session": pa_sess.id},
        )
        assert deact_resp.status_code == 200

        login_resp = await mt_client.post(
            "/api/v1/auth/practitioner-login",
            json={"name": "Free Prac", "email": "freeprac@test.example"},
        )
        assert login_resp.status_code == 403
        detail = login_resp.json()["detail"]
        assert detail["error"] == "org_suspended"
        assert "plan administrator" in detail["message"]

    async def test_reactivating_org_allows_practitioner_login(
        self,
        db_session: AsyncSession,
        mt_client: AsyncClient,
    ) -> None:
        """
        Scenario: Reactivating an org → practitioners can log in.
        """
        pa = await _create_product_admin(db_session, email="pa11@test.example")
        pa_sess = await _create_product_admin_session(db_session, pa.id)
        plan = await _create_plan(db_session, tier="paid")
        org = await _create_org(db_session, name="Reactivate Org", plan_id=plan.id, is_active=False)
        prac = await _create_practitioner(
            db_session, email="reactprac@test.example", org_id=org.id
        )
        await db_session.flush()

        react_resp = await mt_client.patch(
            f"/api/v1/product-admin/organizations/{org.id}/reactivate",
            cookies={"mastery_session": pa_sess.id},
        )
        assert react_resp.status_code == 200

        login_resp = await mt_client.post(
            "/api/v1/auth/practitioner-login",
            json={"name": "React Prac", "email": "reactprac@test.example"},
        )
        assert login_resp.status_code == 200

    async def test_deactivate_practitioner_returns_403_on_login(
        self,
        db_session: AsyncSession,
        mt_client: AsyncClient,
    ) -> None:
        """
        Scenario: Product admin deactivates a practitioner → login returns 403 account_deactivated.
        """
        pa = await _create_product_admin(db_session, email="pa12@test.example")
        pa_sess = await _create_product_admin_session(db_session, pa.id)
        plan = await _create_plan(db_session, tier="paid")
        org = await _create_org(db_session, plan_id=plan.id)
        prac = await _create_practitioner(
            db_session, email="deactprac@test.example", org_id=org.id
        )
        await db_session.flush()

        deact_resp = await mt_client.patch(
            f"/api/v1/product-admin/practitioners/{prac.id}/deactivate",
            cookies={"mastery_session": pa_sess.id},
        )
        assert deact_resp.status_code == 200

        login_resp = await mt_client.post(
            "/api/v1/auth/practitioner-login",
            json={"name": "Deact Prac", "email": "deactprac@test.example"},
        )
        assert login_resp.status_code == 403
        assert login_resp.json()["detail"]["error"] == "account_deactivated"

    async def test_force_logout_practitioner_sessions_deleted_on_deactivation(
        self,
        db_session: AsyncSession,
        mt_client: AsyncClient,
    ) -> None:
        """
        Scenario: Force-logout practitioner: session count = 0 after deactivation.
          Given a practitioner with an active session
          When PATCH /product-admin/practitioners/{id}/deactivate is called
          Then no sessions remain for that practitioner
        """
        pa = await _create_product_admin(db_session, email="pa13@test.example")
        pa_sess = await _create_product_admin_session(db_session, pa.id)
        plan = await _create_plan(db_session, tier="paid")
        org = await _create_org(db_session, plan_id=plan.id)
        prac = await _create_practitioner(
            db_session, email="logoutprac@test.example", org_id=org.id
        )
        prac_sess = await _create_prac_session(db_session, prac.id)
        await db_session.flush()

        deact_resp = await mt_client.patch(
            f"/api/v1/product-admin/practitioners/{prac.id}/deactivate",
            cookies={"mastery_session": pa_sess.id},
        )
        assert deact_resp.status_code == 200

        # Verify sessions are gone
        result = await db_session.execute(
            select(SessionModel).where(
                SessionModel.practitioner_id == prac.id,
                SessionModel.identity_type == "practitioner",
            )
        )
        assert result.scalars().all() == []

    async def test_force_logout_org_all_practitioner_sessions_deleted(
        self,
        db_session: AsyncSession,
        mt_client: AsyncClient,
    ) -> None:
        """
        Scenario: Force-logout org: all practitioner sessions deleted on org deactivation.
          Given 3 practitioners in an org, each with an active session
          When PATCH /product-admin/organizations/{id}/deactivate is called
          Then all 3 practitioner sessions are deleted
        """
        pa = await _create_product_admin(db_session, email="pa14@test.example")
        pa_sess = await _create_product_admin_session(db_session, pa.id)
        plan = await _create_plan(db_session, tier="enterprise", nudges_enabled=True)
        org = await _create_org(db_session, plan_id=plan.id)

        prac_ids = []
        for i in range(3):
            prac = await _create_practitioner(
                db_session, email=f"orgprac{i}@test.example", org_id=org.id
            )
            prac_ids.append(prac.id)
            await _create_prac_session(db_session, prac.id)

        await db_session.flush()

        deact_resp = await mt_client.patch(
            f"/api/v1/product-admin/organizations/{org.id}/deactivate",
            cookies={"mastery_session": pa_sess.id},
        )
        assert deact_resp.status_code == 200

        for pid in prac_ids:
            result = await db_session.execute(
                select(SessionModel).where(
                    SessionModel.practitioner_id == pid,
                    SessionModel.identity_type == "practitioner",
                )
            )
            assert result.scalars().all() == [], f"Sessions still exist for practitioner {pid}"

    async def test_activation_precedence_account_deactivated_wins(
        self,
        db_session: AsyncSession,
        mt_client: AsyncClient,
    ) -> None:
        """
        Scenario: Practitioner is_active=false AND org is_active=false → account_deactivated.
          Given a practitioner marked is_active=False in a suspended org
          When practitioner-login is called
          Then 403 account_deactivated is returned (not org_suspended)
        """
        plan = await _create_plan(db_session, tier="free")
        org = await _create_org(db_session, plan_id=plan.id, is_active=False)
        prac = await _create_practitioner(
            db_session,
            email="bothdeact@test.example",
            org_id=org.id,
            is_active=False,
        )
        await db_session.flush()

        login_resp = await mt_client.post(
            "/api/v1/auth/practitioner-login",
            json={"name": "Both Deact", "email": "bothdeact@test.example"},
        )
        assert login_resp.status_code == 403
        # account_deactivated check runs before org_suspended check
        assert login_resp.json()["detail"]["error"] == "account_deactivated"


# ══════════════════════════════════════════════════════════════════════════════
# Step 22.5 — Enrollment and registration scenarios
# ══════════════════════════════════════════════════════════════════════════════

class TestStep225Enrollment:
    async def test_new_practitioner_with_valid_code_linked_to_org(
        self,
        db_session: AsyncSession,
        mt_client: AsyncClient,
    ) -> None:
        """
        Scenario: New practitioner + valid code → linked to the code's org.
          Given an org with an active enrollment code
          When POST /auth/practitioner-login is called with that code and a new email
          Then the created practitioner has organization_id = that org's id
        """
        plan = await _create_plan(db_session, tier="enterprise", nudges_enabled=True)
        org = await _create_org(db_session, plan_id=plan.id)
        await _create_code(db_session, org_id=org.id, code="VALID1234CODE567")
        await db_session.flush()

        resp = await mt_client.post(
            "/api/v1/auth/practitioner-login",
            json={
                "name": "New User",
                "email": "newuser_valid_code@test.example",
                "enrollment_code": "VALID1234CODE567",
            },
        )
        assert resp.status_code == 200, resp.text
        prac_id = resp.json()["practitioner_id"]

        result = await db_session.execute(
            select(Practitioner).where(Practitioner.id == prac_id)
        )
        prac = result.scalar_one()
        assert prac.organization_id == org.id

    async def test_new_practitioner_no_code_linked_to_free_tier(
        self,
        db_session: AsyncSession,
        mt_client: AsyncClient,
    ) -> None:
        """
        Scenario: New practitioner + no code → linked to Free Tier org.
          Given no enrollment code
          When POST /auth/practitioner-login is called
          Then the created practitioner has organization_id = FREE_TIER_ORG_ID
        """
        from app.api.routes.auth import FREE_TIER_ORG_ID

        # Ensure free tier org exists (normally seeded by migration)
        plan = await _create_plan(db_session, tier="free")
        free_tier_org = Organization(
            id=FREE_TIER_ORG_ID,
            name="Free Tier",
            plan_id=plan.id,
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session.add(free_tier_org)
        await db_session.flush()

        resp = await mt_client.post(
            "/api/v1/auth/practitioner-login",
            json={"name": "Free User", "email": "freeuser@test.example"},
        )
        assert resp.status_code == 200, resp.text
        prac_id = resp.json()["practitioner_id"]

        result = await db_session.execute(
            select(Practitioner).where(Practitioner.id == prac_id)
        )
        prac = result.scalar_one()
        assert prac.organization_id == FREE_TIER_ORG_ID

    async def test_new_practitioner_invalid_code_returns_400(
        self,
        db_session: AsyncSession,
        mt_client: AsyncClient,
    ) -> None:
        """
        Scenario: New practitioner + invalid code → 400 invalid_code.
        """
        resp = await mt_client.post(
            "/api/v1/auth/practitioner-login",
            json={
                "name": "Bad Code User",
                "email": "badcode@test.example",
                "enrollment_code": "INVALID00000CODE",
            },
        )
        assert resp.status_code == 400
        assert resp.json()["detail"]["error"] == "invalid_code"

    async def test_existing_practitioner_code_ignored_on_second_login(
        self,
        db_session: AsyncSession,
        mt_client: AsyncClient,
    ) -> None:
        """
        Scenario: Existing practitioner + different code on second login → code ignored; org unchanged.
          Given a practitioner already linked to org A
          When they log in again with a code for org B
          Then the practitioner's org remains org A
        """
        plan = await _create_plan(db_session, tier="enterprise", nudges_enabled=True)
        org_a = await _create_org(db_session, name="Org A", plan_id=plan.id)
        org_b = await _create_org(db_session, name="Org B", plan_id=plan.id)
        await _create_code(db_session, org_id=org_b.id, code="ORGBCODE1234AAAA")

        prac = await _create_practitioner(
            db_session, email="existing@test.example", org_id=org_a.id
        )
        await db_session.flush()

        resp = await mt_client.post(
            "/api/v1/auth/practitioner-login",
            json={
                "name": "Existing",
                "email": "existing@test.example",
                "enrollment_code": "ORGBCODE1234AAAA",
            },
        )
        assert resp.status_code == 200

        await db_session.refresh(prac)
        assert prac.organization_id == org_a.id, "Existing practitioner's org should not change"

    async def test_free_plan_cert_recycling_blocked_after_delete(
        self,
        db_session: AsyncSession,
        mt_client: AsyncClient,
    ) -> None:
        """
        Scenario: Free plan practitioner deletes a profile then tries to recreate same cert → 409.
          Given a practitioner on a free plan (allow_cert_recycling=False)
          And a profile for cert X has been soft-deleted
          When POST .../profiles is called with the same cert X
          Then 409 cert_recycling_blocked is returned
        """
        plan = await _create_plan(db_session, tier="free", allow_recycling=False)
        org = await _create_org(db_session, plan_id=plan.id)
        prac = await _create_practitioner(db_session, org_id=org.id)
        prac_sess = await _create_prac_session(db_session, prac.id)

        cert_id = str(uuid.uuid4())
        # Simulate a soft-deleted profile for that cert
        deleted_profile = PractitionerProfile(
            id=str(uuid.uuid4()),
            practitioner_id=prac.id,
            name="Old Profile",
            is_active=False,
            certification_id=cert_id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            deleted_at=datetime.now(UTC),
        )
        db_session.add(deleted_profile)
        await db_session.flush()

        resp = await mt_client.post(
            f"/api/v1/practitioners/{prac.id}/profiles",
            json={"name": "New Profile", "certification_id": cert_id},
            cookies={"mastery_session": prac_sess.id},
        )
        assert resp.status_code == 409, resp.text
        assert resp.json()["detail"]["error"] == "cert_recycling_blocked"

    async def test_paid_plan_cert_recycling_allowed_after_delete(
        self,
        db_session: AsyncSession,
        mt_client: AsyncClient,
    ) -> None:
        """
        Scenario: Paid plan practitioner deletes a profile then creates a new one → 201.
          Given a practitioner on a paid plan (allow_cert_recycling=True)
          And a profile for cert X has been soft-deleted
          When POST .../profiles is called with the same cert X
          Then 201 is returned (recycling allowed)
        """
        plan = await _create_plan(db_session, tier="paid", allow_recycling=True)
        org = await _create_org(db_session, plan_id=plan.id)
        prac = await _create_practitioner(db_session, org_id=org.id)
        prac_sess = await _create_prac_session(db_session, prac.id)

        cert_id = str(uuid.uuid4())
        deleted_profile = PractitionerProfile(
            id=str(uuid.uuid4()),
            practitioner_id=prac.id,
            name="Old Profile",
            is_active=False,
            certification_id=cert_id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            deleted_at=datetime.now(UTC),
        )
        db_session.add(deleted_profile)
        await db_session.flush()

        resp = await mt_client.post(
            f"/api/v1/practitioners/{prac.id}/profiles",
            json={"name": "New Profile", "certification_id": cert_id},
            cookies={"mastery_session": prac_sess.id},
        )
        assert resp.status_code == 201, resp.text


# ══════════════════════════════════════════════════════════════════════════════
# Step 22.6 — Plan enforcement scenarios
# ══════════════════════════════════════════════════════════════════════════════

class TestStep226PlanEnforcement:
    async def test_free_plan_profile_limit_blocks_third_profile(
        self,
        db_session: AsyncSession,
        mt_client: AsyncClient,
    ) -> None:
        """
        Scenario: Free plan practitioner with 2 profiles tries 3rd → 402 profiles limit.
          Given a practitioner on a free plan (max_profiles_per_practitioner=2)
          And the practitioner already has 2 active profiles
          When POST .../profiles is called for a 3rd
          Then the response is 402 with limit_type=profiles
        """
        plan = await _create_plan(db_session, tier="free", max_profiles=2)
        org = await _create_org(db_session, plan_id=plan.id)
        prac = await _create_practitioner(db_session, org_id=org.id)
        prac_sess = await _create_prac_session(db_session, prac.id)

        now = datetime.now(UTC)
        for i in range(2):
            db_session.add(PractitionerProfile(
                id=str(uuid.uuid4()),
                practitioner_id=prac.id,
                name=f"Profile {i}",
                is_active=i == 0,
                created_at=now,
                updated_at=now,
                deleted_at=None,
            ))
        await db_session.flush()

        # certification_id must pass Pydantic validation before the plan check fires.
        # A non-existent UUID is fine here — SQLite skips FK checks and the route
        # returns 402 before it ever looks the cert up.
        resp = await mt_client.post(
            f"/api/v1/practitioners/{prac.id}/profiles",
            json={"name": "Third Profile", "certification_id": "00000000-0000-0000-0000-000000000099"},
            cookies={"mastery_session": prac_sess.id},
        )
        assert resp.status_code == 402, resp.text
        detail = resp.json()["detail"]
        assert detail["error"] == "plan_limit_reached"
        assert detail["limit_type"] == "profiles"

    async def test_enterprise_plan_profile_limit_unlimited(
        self,
        db_session: AsyncSession,
        mt_client: AsyncClient,
    ) -> None:
        """
        Scenario: Enterprise plan practitioner with 10 profiles can create 11th → 201.
          Given a practitioner on an enterprise plan (max_profiles=-1)
          And the practitioner already has 10 profiles
          When POST .../profiles is called for an 11th
          Then the response is 201
        """
        plan = await _create_plan(
            db_session,
            tier="enterprise",
            max_profiles=-1,
            nudges_enabled=True,
            allow_recycling=True,
        )
        org = await _create_org(db_session, plan_id=plan.id)
        prac = await _create_practitioner(db_session, org_id=org.id)
        prac_sess = await _create_prac_session(db_session, prac.id)

        now = datetime.now(UTC)
        for i in range(10):
            db_session.add(PractitionerProfile(
                id=str(uuid.uuid4()),
                practitioner_id=prac.id,
                name=f"Profile {i}",
                is_active=i == 0,
                created_at=now,
                updated_at=now,
                deleted_at=None,
            ))
        await db_session.flush()

        # certification_id must pass Pydantic validation; the cert doesn't need to
        # exist in the DB (SQLite skips FK checks) — route succeeds and returns cert_code=None.
        resp = await mt_client.post(
            f"/api/v1/practitioners/{prac.id}/profiles",
            json={"name": "Eleventh Profile", "certification_id": "00000000-0000-0000-0000-000000000099"},
            cookies={"mastery_session": prac_sess.id},
        )
        assert resp.status_code == 201, resp.text

    async def test_free_plan_learning_path_limit_blocks_third(
        self,
        db_session: AsyncSession,
        mt_client: AsyncClient,
    ) -> None:
        """
        Scenario: Free plan practitioner with 2 learning paths tries 3rd → 402 learning_paths limit.
          Given a practitioner on a free plan (max_learning_paths=2)
          And the practitioner already has 2 learning paths
          When POST /learning-paths/generate is called
          Then the response is 402 with limit_type=learning_paths

        Note: This test calls the generate endpoint which triggers the actual workflow.
        We stub it by checking the plan enforcer directly via the plan enforcer unit.
        """
        from app.api.deps.plan import get_plan_enforcer
        from app.db.models import LearningPath

        plan = await _create_plan(db_session, tier="free", max_paths=2)
        org = await _create_org(db_session, plan_id=plan.id)
        prac = await _create_practitioner(db_session, org_id=org.id)

        now = datetime.now(UTC)
        for i in range(2):
            db_session.add(LearningPath(
                id=str(uuid.uuid4()),
                practitioner_id=prac.id,
                status="draft",
                generated_at=now,
            ))
        await db_session.flush()

        enforcer = await get_plan_enforcer(prac.id, db_session)
        with pytest.raises(Exception) as exc_info:
            await enforcer.check_learning_path_count(db_session, prac.id)

        # Should raise HTTPException(status_code=402)
        exc = exc_info.value
        assert exc.status_code == 402  # type: ignore[attr-defined]
        assert exc.detail["limit_type"] == "learning_paths"  # type: ignore[index]


# ══════════════════════════════════════════════════════════════════════════════
# Product admin password rotation policy
# ══════════════════════════════════════════════════════════════════════════════

class TestProductAdminPasswordRotation:
    """Scenarios for the 30-day forced rotation policy (Phase 22 follow-up)."""

    async def test_first_login_with_must_change_password_true_returns_must_change(
        self,
        db_session: AsyncSession,
        mt_client: AsyncClient,
    ) -> None:
        """
        Scenario: Freshly seeded product admin logs in → must_change_password=True.
          Given a product admin with must_change_password=True and password_changed_at=NULL
          When POST /product-admin/login is called with correct credentials
          Then the response contains must_change_password=True
        """
        await _create_product_admin(
            db_session,
            email="firstlogin@test.example",
            must_change_password=True,
        )
        await db_session.flush()

        resp = await mt_client.post(
            "/api/v1/product-admin/login",
            json={"email": "firstlogin@test.example", "password": "Welcome1!"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["must_change_password"] is True

    async def test_login_with_stale_password_triggers_rotation(
        self,
        db_session: AsyncSession,
        mt_client: AsyncClient,
    ) -> None:
        """
        Scenario: Product admin whose password is 31+ days old → rotation forced on login.
          Given a product admin with must_change_password=False
            And password_changed_at is 31 days in the past
          When POST /product-admin/login is called
          Then must_change_password=True is returned (rotation triggered)
        """
        pa = ProductAdminUser(
            id=str(uuid.uuid4()),
            email="stale@test.example",
            password_hash=_hash("Welcome1!"),
            first_name="StaleAdmin",
            must_change_password=False,
            password_changed_at=datetime.now(UTC) - timedelta(days=31),
            created_at=datetime.now(UTC),
        )
        db_session.add(pa)
        await db_session.flush()

        resp = await mt_client.post(
            "/api/v1/product-admin/login",
            json={"email": "stale@test.example", "password": "Welcome1!"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["must_change_password"] is True

    async def test_login_with_null_password_changed_at_triggers_rotation(
        self,
        db_session: AsyncSession,
        mt_client: AsyncClient,
    ) -> None:
        """
        Scenario: Product admin with must_change_password=False but password_changed_at=NULL
          triggers rotation (account was seeded/migrated before the rotation policy was added).
          Given must_change_password=False and password_changed_at=NULL
          When POST /product-admin/login is called
          Then must_change_password=True is returned
        """
        pa = ProductAdminUser(
            id=str(uuid.uuid4()),
            email="nulldate@test.example",
            password_hash=_hash("Welcome1!"),
            first_name="NullAdmin",
            must_change_password=False,
            password_changed_at=None,
            created_at=datetime.now(UTC),
        )
        db_session.add(pa)
        await db_session.flush()

        resp = await mt_client.post(
            "/api/v1/product-admin/login",
            json={"email": "nulldate@test.example", "password": "Welcome1!"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["must_change_password"] is True

    async def test_login_with_fresh_password_does_not_trigger_rotation(
        self,
        db_session: AsyncSession,
        mt_client: AsyncClient,
    ) -> None:
        """
        Scenario: Product admin whose password was changed within the last 30 days → no rotation.
          Given must_change_password=False and password_changed_at=10 days ago
          When POST /product-admin/login is called
          Then must_change_password=False is returned (rotation not triggered)
        """
        pa = ProductAdminUser(
            id=str(uuid.uuid4()),
            email="fresh@test.example",
            password_hash=_hash("Welcome1!"),
            first_name="FreshAdmin",
            must_change_password=False,
            password_changed_at=datetime.now(UTC) - timedelta(days=10),
            created_at=datetime.now(UTC),
        )
        db_session.add(pa)
        await db_session.flush()

        resp = await mt_client.post(
            "/api/v1/product-admin/login",
            json={"email": "fresh@test.example", "password": "Welcome1!"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["must_change_password"] is False

    async def test_change_password_resets_rotation_clock(
        self,
        db_session: AsyncSession,
        mt_client: AsyncClient,
    ) -> None:
        """
        Scenario: After change-password succeeds, subsequent login does not trigger rotation.
          Given a product admin whose password is 31 days old (rotation due)
          When POST /product-admin/change-password is called successfully
            And POST /product-admin/login is called again
          Then the second login returns must_change_password=False
        """
        # Create admin with stale password (rotation due)
        pa = ProductAdminUser(
            id=str(uuid.uuid4()),
            email="rotate@test.example",
            password_hash=_hash("OldPass1!"),
            first_name="RotateAdmin",
            must_change_password=False,
            password_changed_at=datetime.now(UTC) - timedelta(days=31),
            created_at=datetime.now(UTC),
        )
        db_session.add(pa)
        await db_session.flush()

        # Step 1 — login triggers rotation flag
        r1 = await mt_client.post(
            "/api/v1/product-admin/login",
            json={"email": "rotate@test.example", "password": "OldPass1!"},
        )
        assert r1.status_code == 200
        assert r1.json()["must_change_password"] is True

        # Capture session cookie from Set-Cookie header (httpx ASGITransport does not
        # persist Secure cookies to non-HTTPS test URLs, so pass it explicitly).
        from app.config import settings as _cfg
        session_cookie = r1.cookies.get(_cfg.session_cookie_name)
        assert session_cookie, "Expected session cookie after login"

        # Step 2 — change password
        r2 = await mt_client.post(
            "/api/v1/product-admin/change-password",
            json={"current_password": "OldPass1!", "new_password": "NewPass2@"},
            cookies={_cfg.session_cookie_name: session_cookie},
        )
        assert r2.status_code == 204, r2.text

        # Step 3 — re-login confirms rotation clock reset (must_change_password=False)
        r3 = await mt_client.post(
            "/api/v1/product-admin/login",
            json={"email": "rotate@test.example", "password": "NewPass2@"},
        )
        assert r3.status_code == 200
        assert r3.json()["must_change_password"] is False
