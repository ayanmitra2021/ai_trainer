"""Auth API — Step 5.2.

Routes:
  POST /auth/practitioner-login   upsert practitioner by email, create session, set cookie
  POST /auth/admin-login          verify admin password, create session, set cookie
  POST /auth/logout               delete session, clear cookie
  POST /auth/change-password      admin-only; verifies current pw, sets new pw
  GET  /auth/me                   returns current session identity
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import bcrypt as _bcrypt_lib

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import Response as FastAPIResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.session import (
    SessionInfo,
    get_session,
    require_admin,
)
from app.config import settings
from app.db.models import AdminUser
from app.db.models import Certification
from app.db.models import PractitionerProfile
from app.db.models import Session as SessionModel
from app.db.models import Practitioner
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


def _hash_pw(password: str) -> str:
    return _bcrypt_lib.hashpw(password.encode(), _bcrypt_lib.gensalt()).decode()


def _verify_pw(plain: str, hashed: str) -> bool:
    return _bcrypt_lib.checkpw(plain.encode(), hashed.encode())


# ── Pydantic schemas ───────────────────────────────────────────────────────────

class PractitionerLoginRequest(BaseModel):
    name: str
    email: str
    role: str = ""
    practice: str = ""
    seniority_level: str = ""


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


# ── Practitioner login ─────────────────────────────────────────────────────────

@router.post("/practitioner-login", response_model=PractitionerLoginResponse)
async def practitioner_login(
    body: PractitionerLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> PractitionerLoginResponse:
    """Upsert practitioner by email; create session; set HTTP-only cookie.

    Name and org_level are always overwritten so re-entry reflects current org state.
    """
    from sqlalchemy import select

    result = await db.execute(
        select(Practitioner).where(Practitioner.email == body.email)
    )
    practitioner = result.scalar_one_or_none()

    if practitioner is None:
        practitioner = Practitioner(
            id=str(uuid.uuid4()),
            name=body.name,
            email=body.email,
            role=body.role or None,
            practice=body.practice or None,
            seniority_level=body.seniority_level or None,
        )
        db.add(practitioner)
        await db.flush()
    else:
        # Overwrite all editable fields — form values always win
        practitioner.name = body.name
        practitioner.role = body.role or None
        practitioner.practice = body.practice or None
        if body.seniority_level:
            practitioner.seniority_level = body.seniority_level
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
    from sqlalchemy import select

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
    from sqlalchemy import select

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
    from sqlalchemy import select as sa_select

    active_profile_id: str | None = None
    active_certification_code: str | None = None

    if session.identity_type == "practitioner" and session.practitioner_id:
        result = await db.execute(
            sa_select(PractitionerProfile).where(
                PractitionerProfile.practitioner_id == session.practitioner_id,
                PractitionerProfile.is_active.is_(True),
            )
        )
        active_profile = result.scalar_one_or_none()
        if active_profile is not None:
            active_profile_id = active_profile.id
            if active_profile.certification_id:
                cert = await db.get(Certification, active_profile.certification_id)
                if cert:
                    active_certification_code = cert.code

    return MeResponse(
        identity_type=session.identity_type,
        first_name=session.first_name,
        practitioner_id=session.practitioner_id,
        admin_role=session.admin_role,
        must_change_password=session.must_change_password,
        active_profile_id=active_profile_id,
        active_certification_code=active_certification_code,
    )
