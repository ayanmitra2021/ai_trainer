"""Session dependency providers — Step 5.2.

Usage in route handlers
-----------------------
Read-only authenticated data:
    session: SessionInfo = Depends(require_any_authenticated)

Practitioner-only route (add self-enforcement inline for data isolation):
    session: SessionInfo = Depends(require_practitioner)
    enforce_self_or_admin(session, practitioner_id)   # raises 403 if denied

Admin-only routes (observability, pulse trigger):
    session: SessionInfo = Depends(require_admin)

Admin + leadership routes (rollups, nudge view):
    session: SessionInfo = Depends(require_admin_or_leadership)

Product-admin-only routes (platform management — Phase 22):
    session: SessionInfo = Depends(require_product_admin)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import AdminUser
from app.db.models import ProductAdminUser
from app.db.models import Session as SessionModel
from app.db.session import get_db


@dataclass
class SessionInfo:
    """Resolved identity attached to a validated request session."""

    session_id: str
    identity_type: Literal["practitioner", "admin", "product_admin"]
    practitioner_id: str | None
    admin_user_id: str | None
    admin_role: str | None  # "admin" | "leadership" | None
    first_name: str
    must_change_password: bool = field(default=False)
    product_admin_user_id: str | None = field(default=None)


async def get_session(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SessionInfo:
    """Read the session cookie, validate against the DB, return a SessionInfo.

    Raises 401 if the cookie is absent or the session row is not found.
    Raises 401 if an admin or product_admin session has passed its expiry time.
    Updates last_seen_at on every valid request.
    """
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = await db.get(SessionModel, token)
    if session is None:
        raise HTTPException(status_code=401, detail="Session not found or expired")

    now = datetime.now(UTC)

    # Check expiry for admin and product_admin sessions.
    # SQLite returns DateTime columns without tzinfo (offset-naive); normalise to
    # UTC before comparing so the check is correct in both Postgres and SQLite.
    expires_at = session.expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at is not None and now > expires_at:
        await db.delete(session)
        await db.commit()
        raise HTTPException(status_code=401, detail="Session expired — please log in again")

    # Refresh the admin / product_admin session expiry window on activity
    if session.identity_type in ("admin", "product_admin") and session.expires_at is not None:
        session.expires_at = now + timedelta(hours=settings.admin_session_timeout_hours)

    session.last_seen_at = now
    await db.commit()

    if session.identity_type == "admin":
        admin = await db.get(AdminUser, session.admin_user_id)
        if admin is None:
            raise HTTPException(status_code=401, detail="Admin account not found")
        return SessionInfo(
            session_id=session.id,
            identity_type="admin",
            practitioner_id=None,
            admin_user_id=admin.id,
            admin_role=admin.role,
            first_name=admin.first_name,
            must_change_password=admin.must_change_password,
        )

    if session.identity_type == "product_admin":
        product_admin = await db.get(ProductAdminUser, session.product_admin_user_id)
        if product_admin is None:
            raise HTTPException(status_code=401, detail="Product admin account not found")
        return SessionInfo(
            session_id=session.id,
            identity_type="product_admin",
            practitioner_id=None,
            admin_user_id=None,
            admin_role=None,
            first_name=product_admin.first_name,
            must_change_password=product_admin.must_change_password,
            product_admin_user_id=product_admin.id,
        )

    # Default: practitioner
    from app.db.models import Practitioner

    practitioner = await db.get(Practitioner, session.practitioner_id)
    first_name = practitioner.name.split()[0] if practitioner else "Practitioner"
    return SessionInfo(
        session_id=session.id,
        identity_type="practitioner",
        practitioner_id=session.practitioner_id,
        admin_user_id=None,
        admin_role=None,
        first_name=first_name,
    )


async def require_any_authenticated(
    session: SessionInfo = Depends(get_session),
) -> SessionInfo:
    """Any valid session — practitioner or admin. Blocks must_change_password admins."""
    if session.identity_type == "admin" and session.must_change_password:
        raise HTTPException(
            status_code=403,
            detail="Password change required before accessing data",
        )
    return session


async def require_practitioner(
    session: SessionInfo = Depends(get_session),
) -> SessionInfo:
    """Practitioner sessions only. Use enforce_self_or_admin() for data isolation."""
    if session.identity_type != "practitioner":
        raise HTTPException(status_code=403, detail="Practitioner access required")
    return session


async def require_admin(
    session: SessionInfo = Depends(get_session),
) -> SessionInfo:
    """Full admin sessions only (role = 'admin'). Must-change-password blocks access."""
    if session.identity_type != "admin" or session.admin_role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    if session.must_change_password:
        raise HTTPException(
            status_code=403,
            detail="Password change required before accessing data",
        )
    return session


async def require_admin_or_leadership(
    session: SessionInfo = Depends(get_session),
) -> SessionInfo:
    """Any admin session (admin or leadership role). Must-change-password blocks access."""
    if session.identity_type != "admin":
        raise HTTPException(status_code=403, detail="Admin or leadership access required")
    if session.must_change_password:
        raise HTTPException(
            status_code=403,
            detail="Password change required before accessing data",
        )
    return session


async def require_product_admin(
    session: SessionInfo = Depends(get_session),
) -> SessionInfo:
    """Product admin sessions only (platform-level management — Phase 22)."""
    if session.identity_type != "product_admin":
        raise HTTPException(status_code=403, detail="Product admin access required")
    return session


def enforce_self_or_admin(session: SessionInfo, practitioner_id: str) -> None:
    """Raise 403 unless the session is the owner practitioner or a full admin.

    Call this from route handlers that expose per-practitioner data:
        enforce_self_or_admin(session, practitioner_id)

    Leadership admins are NOT allowed to see individual-level data (only aggregates).
    """
    if session.identity_type == "admin" and session.admin_role == "admin":
        return  # full admin can see any practitioner's data
    if session.identity_type == "practitioner" and session.practitioner_id == practitioner_id:
        return  # practitioner accessing own data
    raise HTTPException(
        status_code=403,
        detail="Access denied: you may only access your own data",
    )
