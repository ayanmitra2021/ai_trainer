"""Admin user management API — list, create, and delete admin/leadership accounts.

All routes require a full admin session (role = 'admin'). Leadership accounts
cannot manage other admin users.

Routes:
  GET    /admin-users           list all admin users
  POST   /admin-users           create a new admin user (temporary password, must change)
  DELETE /admin-users/{id}      remove an admin user (cannot delete self)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import bcrypt as _bcrypt_lib

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response as FastAPIResponse
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Literal

from app.api.deps.session import SessionInfo, require_admin
from app.db.models import AdminUser
from app.db.session import get_db

router = APIRouter(prefix="/admin-users", tags=["admin-users"])


# ── Pydantic schemas ───────────────────────────────────────────────────────────

class AdminUserResponse(BaseModel):
    id: str
    email: str
    first_name: str
    role: str
    must_change_password: bool
    last_login_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminUserCreate(BaseModel):
    email: str
    first_name: str
    role: Literal["admin", "leadership"] = "admin"
    temporary_password: str

    @field_validator("temporary_password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Temporary password must be at least 8 characters")
        return v

    @field_validator("email")
    @classmethod
    def email_lowercase(cls, v: str) -> str:
        return v.strip().lower()


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[AdminUserResponse])
async def list_admin_users(
    db: AsyncSession = Depends(get_db),
    _: SessionInfo = Depends(require_admin),
) -> list[AdminUserResponse]:
    """Return all admin/leadership accounts, ordered by creation date."""
    result = await db.execute(
        select(AdminUser).order_by(AdminUser.created_at)
    )
    users = result.scalars().all()
    return [AdminUserResponse.model_validate(u) for u in users]


@router.post("", response_model=AdminUserResponse, status_code=201)
async def create_admin_user(
    body: AdminUserCreate,
    db: AsyncSession = Depends(get_db),
    _: SessionInfo = Depends(require_admin),
) -> AdminUserResponse:
    """Create a new admin or leadership account.

    The new user is assigned the temporary password and must change it on first login.
    Returns 409 if the email already exists.
    """
    # Check for duplicate email
    existing = await db.execute(
        select(AdminUser).where(AdminUser.email == body.email)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=409,
            detail=f"An admin account with email '{body.email}' already exists",
        )

    pw_hash = _bcrypt_lib.hashpw(
        body.temporary_password.encode(), _bcrypt_lib.gensalt()
    ).decode()

    new_user = AdminUser(
        id=str(uuid.uuid4()),
        email=body.email,
        first_name=body.first_name,
        password_hash=pw_hash,
        role=body.role,
        must_change_password=True,
        created_at=datetime.now(UTC),
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return AdminUserResponse.model_validate(new_user)


@router.delete("/{admin_user_id}", status_code=204)
async def delete_admin_user(
    admin_user_id: str,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_admin),
) -> FastAPIResponse:
    """Delete an admin/leadership account.

    Returns 404 if the user doesn't exist.
    Returns 403 if the caller tries to delete their own account.
    """
    if admin_user_id == session.admin_user_id:
        raise HTTPException(
            status_code=403,
            detail="You cannot delete your own account",
        )

    user = await db.get(AdminUser, admin_user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Admin user not found")

    await db.delete(user)
    await db.commit()
    return FastAPIResponse(status_code=204)
