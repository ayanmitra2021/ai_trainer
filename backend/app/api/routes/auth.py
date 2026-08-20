"""Auth API — Step 5.2.

Routes:
  POST /auth/practitioner-login   upsert practitioner by email, create session, set cookie
  POST /auth/admin-login          verify admin password, create session, set cookie
  POST /auth/logout               delete session, clear cookie
  POST /auth/change-password      admin-only; verifies current pw, sets new pw
  GET  /auth/me                   returns current session identity
  GET  /auth/enrollment-info      public; info about an enrollment code (Phase 22)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import bcrypt as _bcrypt_lib

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import Response as FastAPIResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.session import (
    SessionInfo,
    get_session,
    require_admin,
)
from app.config import settings
from app.db.models import AdminUser
from app.db.models import Certification
from app.db.models import Organization
from app.db.models import OrgEnrollmentCode
from app.db.models import PractitionerProfile
from app.db.models import Session as SessionModel
from app.db.models import Practitioner
from app.db.models import SubscriptionPlan
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

# ── Fixed IDs from Phase 22 migration seed ────────────────────────────────────
FREE_TIER_ORG_ID = "00000000-0000-0000-0000-000000000011"


def _hash_pw(password: str) -> str:
    return _bcrypt_lib.hashpw(password.encode(), _bcrypt_lib.gensalt()).decode()


def _verify_pw(plain: str, hashed: str) -> bool:
    return _bcrypt_lib.checkpw(plain.encode(), hashed.encode())


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

class PractitionerLoginRequest(BaseModel):
    name: str
    email: str
    role: str = ""
    practice: str = ""
    seniority_level: str = ""
    # Phase 22: optional enrollment code for new practitioners
    enrollment_code: str | None = None


class PractitionerLookupResponse(BaseModel):
    found: bool
    name: str = ""
    role: str = ""
    practice: str = ""
    seniority_level: str = ""


class AdminLoginRequest(BaseModel):
    email: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class PractitionerLoginResponse(BaseModel):
    identity_type: str = "practitioner"
    first_name: str
    practitioner_id: str


class AdminLoginResponse(BaseModel):
    identity_type: str = "admin"
    first_name: str
    role: str
    must_change_password: bool


class MeResponse(BaseModel):
    identity_type: str
    first_name: str
    practitioner_id: str | None = None
    admin_role: str | None = None
    must_change_password: bool = False
    active_profile_id: str | None = None
    active_certification_code: str | None = None
    # Phase 9.3: exposed so the frontend can gate wizard access without an extra round-trip.
    active_profile_is_locked: bool | None = None
    # Phase 22: plan tier for the practitioner's org
    plan_tier: str | None = None


class EnrollmentInfoResponse(BaseModel):
    valid: bool
    org_name: str | None = None
    plan_name: str | None = None
    plan_tier: str | None = None


# ── Enrollment info (public) ───────────────────────────────────────────────────

@router.get("/enrollment-info", response_model=EnrollmentInfoResponse)
async def enrollment_info(
    code: str = Query(..., description="16-character enrollment code"),
    db: AsyncSession = Depends(get_db),
) -> EnrollmentInfoResponse:
    """Return info about an enrollment code — public, no auth required."""
    result = await db.execute(
        select(OrgEnrollmentCode).where(
            OrgEnrollmentCode.code == code.strip().upper(),
            OrgEnrollmentCode.is_active.is_(True),
        )
    )
    enrollment_code = result.scalar_one_or_none()
    if enrollment_code is None:
        return EnrollmentInfoResponse(valid=False)

    org = await db.get(Organization, enrollment_code.organization_id)
    if org is None or not org.is_active:
        return EnrollmentInfoResponse(valid=False)

    plan = await db.get(SubscriptionPlan, org.plan_id)
    return EnrollmentInfoResponse(
        valid=True,
        org_name=org.name,
        plan_name=plan.name if plan else None,
        plan_tier=plan.tier if plan else None,
    )


# ── Practitioner login ─────────────────────────────────────────────────────────

@router.post("/practitioner-login", response_model=PractitionerLoginResponse)
async def practitioner_login(
    body: PractitionerLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> PractitionerLoginResponse:
    """Upsert practitioner by email; create session; set HTTP-only cookie.

    Phase 22: enrollment_code on first login links the practitioner to an org.
    On subsequent logins, enrollment_code is silently ignored (org is fixed).
    Org-suspended check runs for all existing practitioners.
    """
    result = await db.execute(
        select(Practitioner).where(Practitioner.email == body.email)
    )
    practitioner = result.scalar_one_or_none()

    if practitioner is None:
        # ── New practitioner ──────────────────────────────────────────────────
        org_id: str | None = None

        if body.enrollment_code:
            code_result = await db.execute(
                select(OrgEnrollmentCode).where(
                    OrgEnrollmentCode.code == body.enrollment_code.strip().upper(),
                    OrgEnrollmentCode.is_active.is_(True),
                )
            )
            enrollment_code = code_result.scalar_one_or_none()
            if enrollment_code is None:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "invalid_code",
                        "message": "The enrollment code is invalid or has already been used.",
                    },
                )
            # Validate org is active and within capacity
            org = await db.get(Organization, enrollment_code.organization_id)
            if org is None or not org.is_active:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "invalid_code",
                        "message": "The enrollment code is invalid or has already been used.",
                    },
                )
            # Check capacity
            plan = await db.get(SubscriptionPlan, org.plan_id)
            if plan and plan.max_practitioners_per_org != -1:
                count_result = await db.execute(
                    select(func.count(Practitioner.id)).where(
                        Practitioner.organization_id == org.id
                    )
                )
                current_count = count_result.scalar_one()
                if current_count >= plan.max_practitioners_per_org:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "error": "org_capacity_reached",
                            "message": "This organization has reached its maximum practitioner count.",
                        },
                    )
            org_id = org.id
        else:
            # Fall back to Free Tier org
            org_id = FREE_TIER_ORG_ID

        practitioner = Practitioner(
            id=str(uuid.uuid4()),
            name=body.name,
            email=body.email,
            role=body.role or None,
            practice=body.practice or None,
            seniority_level=body.seniority_level or None,
            organization_id=org_id,
        )
        db.add(practitioner)
        await db.flush()
    else:
        # ── Existing practitioner ─────────────────────────────────────────────
        # Phase 21: block deactivated accounts before any data is touched
        if not practitioner.is_active:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "account_deactivated",
                    "message": "Your account has been deactivated — please contact your administrator.",
                },
            )

        # Phase 22: check if the org is suspended
        if practitioner.organization_id is not None:
            org = await db.get(Organization, practitioner.organization_id)
            if org is not None and not org.is_active:
                plan = await db.get(SubscriptionPlan, org.plan_id)
                tier = plan.tier if plan else "free"
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "org_suspended",
                        "message": _org_suspended_message(tier),
                    },
                )

        # Overwrite all editable fields — form values always win
        practitioner.name = body.name
        practitioner.role = body.role or None
        practitioner.practice = body.practice or None
        if body.seniority_level:
            practitioner.seniority_level = body.seniority_level
        # enrollment_code is ignored for existing practitioners
        await db.flush()

    # Create session
    session = SessionModel(
        id=str(uuid.uuid4()),
        identity_type="practitioner",
        practitioner_id=practitioner.id,
        admin_user_id=None,
        expires_at=None,  # practitioner sessions don't expire
    )
    db.add(session)
    await db.commit()

    response.set_cookie(
        key=settings.session_cookie_name,
        value=session.id,
        httponly=True,
        samesite="none",   # required for cross-origin cookie (GitHub Pages → Render)
        secure=True,       # SameSite=None requires Secure; localhost is exempt by spec
    )

    first_name = practitioner.name.split()[0]
    return PractitionerLoginResponse(
        first_name=first_name,
        practitioner_id=practitioner.id,
    )


# ── Email lookup (pre-fill) ────────────────────────────────────────────────────

@router.get("/lookup-email", response_model=PractitionerLookupResponse)
async def lookup_email(
    email: str,
    db: AsyncSession = Depends(get_db),
) -> PractitionerLookupResponse:
    """Return existing practitioner fields for a given email (no auth required).

    Called on email field blur during login to pre-fill the rest of the form.
    Returns found=False when the email is new — never a 404, so the frontend
    can treat any successful response uniformly.
    """
    result = await db.execute(
        select(Practitioner).where(Practitioner.email == email.strip().lower())
    )
    practitioner = result.scalar_one_or_none()

    if practitioner is None:
        return PractitionerLookupResponse(found=False)

    return PractitionerLookupResponse(
        found=True,
        name=practitioner.name or "",
        role=practitioner.role or "",
        practice=practitioner.practice or "",
        seniority_level=practitioner.seniority_level or "",
    )


# ── Admin login ────────────────────────────────────────────────────────────────

@router.post("/admin-login", response_model=AdminLoginResponse)
async def admin_login(
    body: AdminLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> AdminLoginResponse:
    """Verify admin credentials; create session; set HTTP-only cookie.

    Does NOT redirect on must_change_password — the frontend handles the redirect.
    """
    result = await db.execute(
        select(AdminUser).where(AdminUser.email == body.email)
    )
    admin = result.scalar_one_or_none()

    if admin is None or not _verify_pw(body.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Create session with expiry
    now = datetime.now(UTC)
    session = SessionModel(
        id=str(uuid.uuid4()),
        identity_type="admin",
        practitioner_id=None,
        admin_user_id=admin.id,
        expires_at=now + timedelta(hours=settings.admin_session_timeout_hours),
    )
    db.add(session)

    admin.last_login_at = now
    await db.commit()

    response.set_cookie(
        key=settings.session_cookie_name,
        value=session.id,
        httponly=True,
        samesite="none",   # required for cross-origin cookie (GitHub Pages → Render)
        secure=True,       # SameSite=None requires Secure; localhost is exempt by spec
    )

    return AdminLoginResponse(
        first_name=admin.first_name,
        role=admin.role,
        must_change_password=admin.must_change_password,
    )


# ── Logout ────────────────────────────────────────────────────────────────────

@router.post("/logout")
async def logout(
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
    # Must pass the same samesite/secure flags used when setting the cookie,
    # otherwise browsers treat it as a different cookie and won't clear it.
    resp.delete_cookie(
        key=settings.session_cookie_name,
        samesite="none",
        secure=True,
    )
    return resp


# ── Change password ────────────────────────────────────────────────────────────

@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(get_session),
) -> FastAPIResponse:
    """Admin-only. Verify current password, update hash, clear must_change_password."""
    if session.identity_type != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    admin = await db.get(AdminUser, session.admin_user_id)
    if admin is None:
        raise HTTPException(status_code=404, detail="Admin account not found")

    if not _verify_pw(body.current_password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    admin.password_hash = _hash_pw(body.new_password)
    admin.must_change_password = False
    await db.commit()
    return FastAPIResponse(status_code=204)


# ── Me ─────────────────────────────────────────────────────────────────────────

@router.get("/me", response_model=MeResponse)
async def me(
    session: SessionInfo = Depends(get_session),
    db: AsyncSession = Depends(get_db),
) -> MeResponse:
    """Return current session identity — used by the frontend on page load."""
    active_profile_id: str | None = None
    active_certification_code: str | None = None
    active_profile_is_locked: bool | None = None
    plan_tier: str | None = None

    if session.identity_type == "practitioner" and session.practitioner_id:
        # Active profile
        result = await db.execute(
            select(PractitionerProfile).where(
                PractitionerProfile.practitioner_id == session.practitioner_id,
                PractitionerProfile.is_active.is_(True),
                PractitionerProfile.deleted_at.is_(None),
            )
        )
        active_profile = result.scalar_one_or_none()
        if active_profile is not None:
            active_profile_id = active_profile.id
            active_profile_is_locked = active_profile.is_locked
            if active_profile.certification_id:
                cert = await db.get(Certification, active_profile.certification_id)
                if cert:
                    active_certification_code = cert.code

        # Phase 22: resolve plan_tier via org
        practitioner = await db.get(Practitioner, session.practitioner_id)
        if practitioner and practitioner.organization_id:
            org = await db.get(Organization, practitioner.organization_id)
            if org:
                plan = await db.get(SubscriptionPlan, org.plan_id)
                if plan:
                    plan_tier = plan.tier

    return MeResponse(
        identity_type=session.identity_type,
        first_name=session.first_name,
        practitioner_id=session.practitioner_id,
        admin_role=session.admin_role,
        must_change_password=session.must_change_password,
        active_profile_id=active_profile_id,
        active_certification_code=active_certification_code,
        active_profile_is_locked=active_profile_is_locked,
        plan_tier=plan_tier,
    )
