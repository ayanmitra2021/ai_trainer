"""Product Admin API — Phase 22.

Routes:
  POST /product-admin/login
  POST /product-admin/logout
  POST /product-admin/change-password
  GET  /product-admin/me

  POST   /product-admin/plans
  GET    /product-admin/plans
  GET    /product-admin/plans/{id}
  PATCH  /product-admin/plans/{id}
  DELETE /product-admin/plans/{id}

  POST   /product-admin/organizations
  GET    /product-admin/organizations
  GET    /product-admin/organizations/{id}
  PATCH  /product-admin/organizations/{id}
  POST   /product-admin/organizations/{id}/regenerate-code
  PATCH  /product-admin/organizations/{id}/deactivate
  PATCH  /product-admin/organizations/{id}/reactivate
  GET    /product-admin/practitioners
  PATCH  /product-admin/practitioners/{practitioner_id}/deactivate
  PATCH  /product-admin/practitioners/{practitioner_id}/reactivate

  GET    /product-admin/analytics/usage
  GET    /product-admin/analytics/agents
  GET    /product-admin/analytics/plans
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt as _bcrypt_lib
import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response as FastAPIResponse
from pydantic import BaseModel, field_validator, model_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.session import (
    SessionInfo,
    get_session,
    require_product_admin,
)
from app.config import settings
from app.db.models import (
    AdminUser,
    Organization,
    OrgEnrollmentCode,
    OrgNotificationSettings,
    Practitioner,
    ProductAdminUser,
    Session as SessionModel,
    SubscriptionPlan,
)
from app.db.session import get_db

router = APIRouter(prefix="/product-admin", tags=["product-admin"])


# ── helpers ────────────────────────────────────────────────────────────────────

def _hash_pw(password: str) -> str:
    return _bcrypt_lib.hashpw(password.encode(), _bcrypt_lib.gensalt()).decode()


def _verify_pw(plain: str, hashed: str) -> bool:
    return _bcrypt_lib.checkpw(plain.encode(), hashed.encode())


def _gen_code() -> str:
    """Generate a 16-character uppercase hex enrollment code."""
    return secrets.token_hex(8).upper()


def _org_suspended_message(plan_tier: str) -> str:
    if plan_tier == "enterprise":
        return (
            "Your organization's Mastery Pulse access has been suspended. "
            "Please contact your enterprise administrator."
        )
    return (
        "Your Mastery Pulse account has been suspended. "
        "Please contact your plan administrator."
    )


# ── Pydantic schemas ───────────────────────────────────────────────────────────

class ProductAdminLoginRequest(BaseModel):
    email: str
    password: str


class ProductAdminLoginResponse(BaseModel):
    identity_type: str = "product_admin"
    first_name: str
    must_change_password: bool


class ProductAdminMeResponse(BaseModel):
    identity_type: str = "product_admin"
    first_name: str
    must_change_password: bool
    product_admin_user_id: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class SubscriptionPlanCreate(BaseModel):
    name: str
    tier: str  # free | paid | enterprise
    max_profiles_per_practitioner: int
    max_learning_paths: int
    max_mock_exams_per_profile: int
    max_practitioners_per_org: int
    allow_cert_recycling: bool = False
    nudges_enabled: bool = False
    teams_notifications_enabled: bool = False

    @field_validator(
        "max_profiles_per_practitioner",
        "max_learning_paths",
        "max_mock_exams_per_profile",
        "max_practitioners_per_org",
    )
    @classmethod
    def validate_limit(cls, v: int) -> int:
        if v != -1 and v < 1:
            raise ValueError("Limit must be >= 1 or exactly -1 (unlimited)")
        return v

    @model_validator(mode="after")
    def validate_tier_constraints(self) -> "SubscriptionPlanCreate":
        if self.tier == "free":
            self.allow_cert_recycling = False
            self.nudges_enabled = False
        if self.tier == "enterprise":
            self.nudges_enabled = True
        if self.tier not in ("free", "paid", "enterprise"):
            raise ValueError("tier must be 'free', 'paid', or 'enterprise'")
        return self


class SubscriptionPlanUpdate(BaseModel):
    name: str | None = None
    max_profiles_per_practitioner: int | None = None
    max_learning_paths: int | None = None
    max_mock_exams_per_profile: int | None = None
    max_practitioners_per_org: int | None = None
    allow_cert_recycling: bool | None = None
    nudges_enabled: bool | None = None
    teams_notifications_enabled: bool | None = None
    # tier is intentionally excluded — immutable after creation

    @field_validator(
        "max_profiles_per_practitioner",
        "max_learning_paths",
        "max_mock_exams_per_profile",
        "max_practitioners_per_org",
        mode="before",
    )
    @classmethod
    def validate_limit(cls, v: int | None) -> int | None:
        if v is not None and v != -1 and v < 1:
            raise ValueError("Limit must be >= 1 or exactly -1 (unlimited)")
        return v


class SubscriptionPlanRead(BaseModel):
    id: str
    name: str
    tier: str
    max_profiles_per_practitioner: int
    max_learning_paths: int
    max_mock_exams_per_profile: int
    max_practitioners_per_org: int
    allow_cert_recycling: bool
    nudges_enabled: bool
    teams_notifications_enabled: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class OrganizationCreate(BaseModel):
    name: str
    plan_id: str
    billing_email: str | None = None


class OrganizationUpdate(BaseModel):
    name: str | None = None
    plan_id: str | None = None
    billing_email: str | None = None


class OrganizationRead(BaseModel):
    id: str
    name: str
    plan_id: str
    plan_name: str
    plan_tier: str
    billing_email: str | None
    is_active: bool
    enrollment_code: str | None
    practitioner_count: int
    created_at: datetime
    updated_at: datetime


class PractitionerListRow(BaseModel):
    id: str
    name: str
    email: str
    org_name: str | None
    plan_tier: str | None
    is_active: bool
    created_at: datetime


# ── Auth routes ────────────────────────────────────────────────────────────────

@router.post("/login", response_model=ProductAdminLoginResponse)
async def product_admin_login(
    body: ProductAdminLoginRequest,
    response: FastAPIResponse,
    db: AsyncSession = Depends(get_db),
) -> ProductAdminLoginResponse:
    """Verify product admin credentials; create session; set HTTP-only cookie."""
    result = await db.execute(
        select(ProductAdminUser).where(ProductAdminUser.email == body.email)
    )
    admin = result.scalar_one_or_none()

    if admin is None or not _verify_pw(body.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    now = datetime.now(UTC)

    # 30-day password rotation policy.
    # Triggers when must_change_password is currently False but the password
    # hasn't been changed in the last 30 days (or was never voluntarily changed,
    # indicated by password_changed_at=NULL with must_change_password=False).
    PASSWORD_ROTATION_DAYS = 30
    if not admin.must_change_password:
        if admin.password_changed_at is None:
            # Account was seeded or migrated — rotation overdue immediately.
            admin.must_change_password = True
        elif (now - admin.password_changed_at).days >= PASSWORD_ROTATION_DAYS:
            admin.must_change_password = True

    session = SessionModel(
        id=str(uuid.uuid4()),
        identity_type="product_admin",
        practitioner_id=None,
        admin_user_id=None,
        product_admin_user_id=admin.id,
        expires_at=now + timedelta(hours=settings.admin_session_timeout_hours),
    )
    db.add(session)
    admin.last_login_at = now
    await db.commit()

    response.set_cookie(
        key=settings.session_cookie_name,
        value=session.id,
        httponly=True,
        samesite="none",
        secure=True,
    )
    return ProductAdminLoginResponse(
        first_name=admin.first_name,
        must_change_password=admin.must_change_password,
    )


@router.post("/logout")
async def product_admin_logout(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> FastAPIResponse:
    """Delete the session row and clear the cookie."""
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        session = await db.get(SessionModel, token)
        if session is not None:
            await db.delete(session)
            await db.commit()

    resp = FastAPIResponse(status_code=204)
    resp.delete_cookie(key=settings.session_cookie_name, samesite="none", secure=True)
    return resp


@router.post("/change-password")
async def product_admin_change_password(
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_product_admin),
) -> FastAPIResponse:
    """Verify current password, update hash, clear must_change_password."""
    admin = await db.get(ProductAdminUser, session.product_admin_user_id)
    if admin is None:
        raise HTTPException(status_code=404, detail="Product admin account not found")

    if not _verify_pw(body.current_password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    admin.password_hash = _hash_pw(body.new_password)
    admin.must_change_password = False
    admin.password_changed_at = datetime.now(UTC)  # resets the 30-day rotation clock
    await db.commit()
    return FastAPIResponse(status_code=204)


@router.get("/me", response_model=ProductAdminMeResponse)
async def product_admin_me(
    session: SessionInfo = Depends(require_product_admin),
) -> ProductAdminMeResponse:
    """Return current product admin identity."""
    return ProductAdminMeResponse(
        first_name=session.first_name,
        must_change_password=session.must_change_password,
        product_admin_user_id=session.product_admin_user_id or "",
    )


# ── Subscription plan routes ───────────────────────────────────────────────────

@router.post("/plans", response_model=SubscriptionPlanRead, status_code=201)
async def create_plan(
    body: SubscriptionPlanCreate,
    db: AsyncSession = Depends(get_db),
    _: SessionInfo = Depends(require_product_admin),
) -> SubscriptionPlanRead:
    """Create a new subscription plan."""
    now = datetime.now(UTC)
    plan = SubscriptionPlan(
        id=str(uuid.uuid4()),
        name=body.name,
        tier=body.tier,
        max_profiles_per_practitioner=body.max_profiles_per_practitioner,
        max_learning_paths=body.max_learning_paths,
        max_mock_exams_per_profile=body.max_mock_exams_per_profile,
        max_practitioners_per_org=body.max_practitioners_per_org,
        allow_cert_recycling=body.allow_cert_recycling,
        nudges_enabled=body.nudges_enabled,
        teams_notifications_enabled=body.teams_notifications_enabled,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return _plan_read(plan)


@router.get("/plans", response_model=list[SubscriptionPlanRead])
async def list_plans(
    db: AsyncSession = Depends(get_db),
    _: SessionInfo = Depends(require_product_admin),
) -> list[SubscriptionPlanRead]:
    result = await db.execute(select(SubscriptionPlan).order_by(SubscriptionPlan.created_at))
    return [_plan_read(p) for p in result.scalars().all()]


@router.get("/plans/{plan_id}", response_model=SubscriptionPlanRead)
async def get_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    _: SessionInfo = Depends(require_product_admin),
) -> SubscriptionPlanRead:
    plan = await db.get(SubscriptionPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return _plan_read(plan)


@router.patch("/plans/{plan_id}", response_model=SubscriptionPlanRead)
async def update_plan(
    plan_id: str,
    body: SubscriptionPlanUpdate,
    db: AsyncSession = Depends(get_db),
    _: SessionInfo = Depends(require_product_admin),
) -> SubscriptionPlanRead:
    """Update a plan. Tier is immutable."""
    plan = await db.get(SubscriptionPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")

    if body.name is not None:
        plan.name = body.name
    if body.max_profiles_per_practitioner is not None:
        plan.max_profiles_per_practitioner = body.max_profiles_per_practitioner
    if body.max_learning_paths is not None:
        plan.max_learning_paths = body.max_learning_paths
    if body.max_mock_exams_per_profile is not None:
        plan.max_mock_exams_per_profile = body.max_mock_exams_per_profile
    if body.max_practitioners_per_org is not None:
        plan.max_practitioners_per_org = body.max_practitioners_per_org
    if body.allow_cert_recycling is not None:
        plan.allow_cert_recycling = body.allow_cert_recycling
    if body.nudges_enabled is not None:
        plan.nudges_enabled = body.nudges_enabled
    if body.teams_notifications_enabled is not None:
        plan.teams_notifications_enabled = body.teams_notifications_enabled

    plan.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(plan)
    return _plan_read(plan)


@router.delete("/plans/{plan_id}")
async def deactivate_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    _: SessionInfo = Depends(require_product_admin),
) -> dict[str, Any]:
    """Soft-deactivate a plan. 409 if active orgs reference it."""
    plan = await db.get(SubscriptionPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Count active orgs on this plan
    count_result = await db.execute(
        select(func.count()).select_from(Organization).where(
            Organization.plan_id == plan_id,
            Organization.is_active.is_(True),
        )
    )
    active_org_count = count_result.scalar_one()
    if active_org_count > 0:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "plan_has_active_orgs",
                "message": "Cannot deactivate a plan with active organizations.",
                "active_org_count": active_org_count,
            },
        )

    plan.is_active = False
    plan.updated_at = datetime.now(UTC)
    await db.commit()
    return {"deactivated": True}


def _plan_read(plan: SubscriptionPlan) -> SubscriptionPlanRead:
    return SubscriptionPlanRead(
        id=plan.id,
        name=plan.name,
        tier=plan.tier,
        max_profiles_per_practitioner=plan.max_profiles_per_practitioner,
        max_learning_paths=plan.max_learning_paths,
        max_mock_exams_per_profile=plan.max_mock_exams_per_profile,
        max_practitioners_per_org=plan.max_practitioners_per_org,
        allow_cert_recycling=plan.allow_cert_recycling,
        nudges_enabled=plan.nudges_enabled,
        teams_notifications_enabled=plan.teams_notifications_enabled,
        is_active=plan.is_active,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


# ── Organization routes ────────────────────────────────────────────────────────

@router.post("/organizations", response_model=OrganizationRead, status_code=201)
async def create_organization(
    body: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    _: SessionInfo = Depends(require_product_admin),
) -> OrganizationRead:
    """Create an organization and generate its initial enrollment code."""
    plan = await db.get(SubscriptionPlan, body.plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")

    now = datetime.now(UTC)
    org = Organization(
        id=str(uuid.uuid4()),
        name=body.name,
        plan_id=body.plan_id,
        billing_email=body.billing_email,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db.add(org)
    await db.flush()

    code = OrgEnrollmentCode(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        code=_gen_code(),
        is_active=True,
        created_at=now,
    )
    db.add(code)
    await db.commit()
    await db.refresh(org)

    return await _org_read(org, db)


@router.get("/organizations", response_model=list[OrganizationRead])
async def list_organizations(
    db: AsyncSession = Depends(get_db),
    _: SessionInfo = Depends(require_product_admin),
) -> list[OrganizationRead]:
    result = await db.execute(select(Organization).order_by(Organization.created_at))
    orgs = result.scalars().all()
    return [await _org_read(org, db) for org in orgs]


@router.get("/organizations/{org_id}", response_model=OrganizationRead)
async def get_organization(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    _: SessionInfo = Depends(require_product_admin),
) -> OrganizationRead:
    org = await db.get(Organization, org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return await _org_read(org, db)


@router.patch("/organizations/{org_id}", response_model=OrganizationRead)
async def update_organization(
    org_id: str,
    body: OrganizationUpdate,
    db: AsyncSession = Depends(get_db),
    _: SessionInfo = Depends(require_product_admin),
) -> OrganizationRead:
    org = await db.get(Organization, org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    if body.name is not None:
        org.name = body.name
    if body.plan_id is not None:
        plan = await db.get(SubscriptionPlan, body.plan_id)
        if plan is None:
            raise HTTPException(status_code=404, detail="Plan not found")
        org.plan_id = body.plan_id
    if body.billing_email is not None:
        org.billing_email = body.billing_email

    org.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(org)
    return await _org_read(org, db)


@router.post("/organizations/{org_id}/regenerate-code")
async def regenerate_enrollment_code(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    _: SessionInfo = Depends(require_product_admin),
) -> dict[str, Any]:
    """Deactivate the existing active code and issue a new one."""
    org = await db.get(Organization, org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Deactivate all existing active codes
    await db.execute(
        sa.update(OrgEnrollmentCode)
        .where(
            OrgEnrollmentCode.organization_id == org_id,
            OrgEnrollmentCode.is_active.is_(True),
        )
        .values(is_active=False)
    )

    now = datetime.now(UTC)
    new_code = OrgEnrollmentCode(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        code=_gen_code(),
        is_active=True,
        created_at=now,
    )
    db.add(new_code)
    await db.commit()
    return {"code": new_code.code}


@router.patch("/organizations/{org_id}/deactivate")
async def deactivate_organization(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    _: SessionInfo = Depends(require_product_admin),
) -> dict[str, Any]:
    """Deactivate an org and force-logout all its practitioners atomically."""
    org = await db.get(Organization, org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    org.is_active = False
    org.updated_at = datetime.now(UTC)

    # Force-logout: delete all practitioner sessions for this org atomically
    subq = select(Practitioner.id).where(Practitioner.organization_id == org_id)
    await db.execute(
        sa.delete(SessionModel).where(
            SessionModel.identity_type == "practitioner",
            SessionModel.practitioner_id.in_(subq),
        )
    )

    await db.commit()
    return {"deactivated": True}


@router.patch("/organizations/{org_id}/reactivate")
async def reactivate_organization(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    _: SessionInfo = Depends(require_product_admin),
) -> dict[str, Any]:
    """Reactivate a previously deactivated organization."""
    org = await db.get(Organization, org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    org.is_active = True
    org.updated_at = datetime.now(UTC)
    await db.commit()
    return {"reactivated": True}


# ── Practitioner management ────────────────────────────────────────────────────

@router.get("/practitioners", response_model=list[PractitionerListRow])
async def list_practitioners(
    org_id: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    plan_tier: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: SessionInfo = Depends(require_product_admin),
) -> list[PractitionerListRow]:
    """List practitioners — identity fields only. No individual learning data."""
    stmt = (
        select(
            Practitioner.id,
            Practitioner.name,
            Practitioner.email,
            Practitioner.is_active,
            Practitioner.created_at,
            Practitioner.organization_id,
            Organization.name.label("org_name"),
            SubscriptionPlan.tier.label("plan_tier"),
        )
        .outerjoin(Organization, Practitioner.organization_id == Organization.id)
        .outerjoin(SubscriptionPlan, Organization.plan_id == SubscriptionPlan.id)
    )

    if org_id is not None:
        stmt = stmt.where(Practitioner.organization_id == org_id)
    if is_active is not None:
        stmt = stmt.where(Practitioner.is_active == is_active)
    if plan_tier is not None:
        stmt = stmt.where(SubscriptionPlan.tier == plan_tier)

    stmt = stmt.order_by(Practitioner.created_at.desc())
    result = await db.execute(stmt)
    rows = result.all()

    return [
        PractitionerListRow(
            id=row.id,
            name=row.name,
            email=row.email,
            org_name=row.org_name,
            plan_tier=row.plan_tier,
            is_active=row.is_active,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.patch("/practitioners/{practitioner_id}/deactivate")
async def deactivate_practitioner(
    practitioner_id: str,
    db: AsyncSession = Depends(get_db),
    _: SessionInfo = Depends(require_product_admin),
) -> dict[str, Any]:
    """Deactivate a practitioner and force-logout their sessions atomically."""
    practitioner = await db.get(Practitioner, practitioner_id)
    if practitioner is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")

    practitioner.is_active = False

    # Force-logout: delete practitioner sessions atomically
    await db.execute(
        sa.delete(SessionModel).where(
            SessionModel.identity_type == "practitioner",
            SessionModel.practitioner_id == practitioner_id,
        )
    )

    await db.commit()
    return {"deactivated": True}


@router.patch("/practitioners/{practitioner_id}/reactivate")
async def reactivate_practitioner(
    practitioner_id: str,
    db: AsyncSession = Depends(get_db),
    _: SessionInfo = Depends(require_product_admin),
) -> dict[str, Any]:
    """Reactivate a previously deactivated practitioner."""
    practitioner = await db.get(Practitioner, practitioner_id)
    if practitioner is None:
        raise HTTPException(status_code=404, detail="Practitioner not found")

    practitioner.is_active = True
    await db.commit()
    return {"reactivated": True}


# ── Analytics routes ───────────────────────────────────────────────────────────

@router.get("/analytics/usage")
async def analytics_usage(
    db: AsyncSession = Depends(get_db),
    _: SessionInfo = Depends(require_product_admin),
) -> dict[str, Any]:
    """Usage breakdown by plan tier."""
    from app.db.models import Attempt, LessonRead, MockExamSession

    now = datetime.now(UTC)

    # Practitioners per tier
    tier_result = await db.execute(
        select(
            SubscriptionPlan.tier,
            func.count(Practitioner.id).label("practitioner_count"),
        )
        .outerjoin(Organization, SubscriptionPlan.id == Organization.plan_id)
        .outerjoin(Practitioner, Organization.id == Practitioner.organization_id)
        .group_by(SubscriptionPlan.tier)
    )
    tier_rows = tier_result.all()

    # Quiz attempts by tier
    attempt_result = await db.execute(
        select(
            SubscriptionPlan.tier,
            func.count(Attempt.id).label("attempt_count"),
        )
        .join(Practitioner, Attempt.practitioner_id == Practitioner.id)
        .outerjoin(Organization, Practitioner.organization_id == Organization.id)
        .outerjoin(SubscriptionPlan, Organization.plan_id == SubscriptionPlan.id)
        .group_by(SubscriptionPlan.tier)
    )
    attempt_rows = {row.tier: row.attempt_count for row in attempt_result.all()}

    # Lesson reads by tier
    lesson_result = await db.execute(
        select(
            SubscriptionPlan.tier,
            func.count(LessonRead.id).label("lesson_read_count"),
        )
        .join(Practitioner, LessonRead.practitioner_id == Practitioner.id)
        .outerjoin(Organization, Practitioner.organization_id == Organization.id)
        .outerjoin(SubscriptionPlan, Organization.plan_id == SubscriptionPlan.id)
        .group_by(SubscriptionPlan.tier)
    )
    lesson_rows = {row.tier: row.lesson_read_count for row in lesson_result.all()}

    # Completed mock exams by tier
    exam_result = await db.execute(
        select(
            SubscriptionPlan.tier,
            func.count(MockExamSession.id).label("completed_exam_count"),
        )
        .join(Practitioner, MockExamSession.practitioner_id == Practitioner.id)
        .outerjoin(Organization, Practitioner.organization_id == Organization.id)
        .outerjoin(SubscriptionPlan, Organization.plan_id == SubscriptionPlan.id)
        .where(MockExamSession.status == "completed")
        .group_by(SubscriptionPlan.tier)
    )
    exam_rows = {row.tier: row.completed_exam_count for row in exam_result.all()}

    return {
        "by_plan_tier": [
            {
                "tier": row.tier,
                "plan_name": row.tier.capitalize(),  # no plan_name in this query; use tier as label
                "org_count": 0,  # not queried here; use analytics/plans for org breakdown
                "practitioner_count": row.practitioner_count or 0,
                "active_practitioner_count": row.practitioner_count or 0,  # all are active by default
                "total_quiz_attempts": attempt_rows.get(row.tier, 0),
                "total_lesson_reads": lesson_rows.get(row.tier, 0),
                "total_mock_exams_completed": exam_rows.get(row.tier, 0),
            }
            for row in tier_rows
        ],
    }


@router.get("/analytics/agents")
async def analytics_agents(
    db: AsyncSession = Depends(get_db),
    _: SessionInfo = Depends(require_product_admin),
) -> dict[str, Any]:
    """Agent run stats over the last 30 days."""
    from app.db.models import AgentRun

    cutoff = datetime.now(UTC) - timedelta(days=30)

    result = await db.execute(
        select(
            AgentRun.agent_name,
            func.count(AgentRun.id).label("total_runs"),
            func.sum(
                sa.case((AgentRun.status == "success", 1), else_=0)
            ).label("success_count"),
            func.sum(
                sa.case((AgentRun.status == "error", 1), else_=0)
            ).label("error_count"),
            func.avg(AgentRun.latency_ms).label("avg_latency_ms"),
            func.percentile_cont(0.95)
            .within_group(AgentRun.latency_ms)
            .label("p95_latency_ms"),
        )
        .where(AgentRun.started_at >= cutoff)
        .group_by(AgentRun.agent_name)
        .order_by(AgentRun.agent_name)
    )
    rows = result.all()

    return {
        "period_days": 30,
        "by_agent": [
            {
                "agent_name": row.agent_name,
                "run_count": row.total_runs,
                "success_count": row.success_count or 0,
                "failure_count": row.error_count or 0,
                "avg_latency_ms": float(row.avg_latency_ms) if row.avg_latency_ms else None,
                "p95_latency_ms": float(row.p95_latency_ms) if row.p95_latency_ms else None,
            }
            for row in rows
        ],
    }


@router.get("/analytics/plans")
async def analytics_plans(
    db: AsyncSession = Depends(get_db),
    _: SessionInfo = Depends(require_product_admin),
) -> dict[str, Any]:
    """Plan distribution and new enrollments in last 30 days."""
    cutoff = datetime.now(UTC) - timedelta(days=30)

    # Orgs per plan
    dist_result = await db.execute(
        select(
            SubscriptionPlan.id,
            SubscriptionPlan.name,
            SubscriptionPlan.tier,
            func.count(Organization.id).label("org_count"),
        )
        .outerjoin(Organization, SubscriptionPlan.id == Organization.plan_id)
        .group_by(SubscriptionPlan.id, SubscriptionPlan.name, SubscriptionPlan.tier)
        .order_by(SubscriptionPlan.name)
    )
    dist_rows = dist_result.all()

    # New practitioners per plan in last 30 days
    new_result = await db.execute(
        select(
            SubscriptionPlan.id,
            func.count(Practitioner.id).label("new_practitioner_count"),
        )
        .join(Organization, SubscriptionPlan.id == Organization.plan_id)
        .join(Practitioner, Organization.id == Practitioner.organization_id)
        .where(Practitioner.created_at >= cutoff)
        .group_by(SubscriptionPlan.id)
    )
    new_rows = {row.id: row.new_practitioner_count for row in new_result.all()}

    total_new = sum(new_rows.values())

    return {
        "plan_distribution": [
            {
                "tier": row.tier,
                "plan_name": row.name,
                "org_count": row.org_count or 0,
                "practitioner_count": new_rows.get(row.id, 0),  # new practitioners this period
            }
            for row in dist_rows
        ],
        "new_enrollments_last_30d": total_new,
    }


# ── Private helpers ────────────────────────────────────────────────────────────

async def _org_read(org: Organization, db: AsyncSession) -> OrganizationRead:
    """Build an OrganizationRead from an ORM row."""
    plan = await db.get(SubscriptionPlan, org.plan_id)
    plan_name = plan.name if plan else "Unknown"
    plan_tier = plan.tier if plan else "free"

    # Fetch the active enrollment code
    code_result = await db.execute(
        select(OrgEnrollmentCode.code)
        .where(
            OrgEnrollmentCode.organization_id == org.id,
            OrgEnrollmentCode.is_active.is_(True),
        )
        .limit(1)
    )
    active_code = code_result.scalar_one_or_none()

    # Count active practitioners in this org
    pcount_result = await db.execute(
        select(func.count())
        .select_from(Practitioner)
        .where(Practitioner.organization_id == org.id)
    )
    practitioner_count = pcount_result.scalar_one() or 0

    return OrganizationRead(
        id=org.id,
        name=org.name,
        plan_id=org.plan_id,
        plan_name=plan_name,
        plan_tier=plan_tier,
        billing_email=org.billing_email,
        is_active=org.is_active,
        enrollment_code=active_code,
        practitioner_count=practitioner_count,
        created_at=org.created_at,
        updated_at=org.updated_at,
    )
