"""Organization notification settings API — Phase 22.10.

Routes:
  GET  /admin/notification-settings          get (or auto-create) org's settings
  PUT  /admin/notification-settings          upsert settings
  POST /admin/notification-settings/test-teams  send a test Teams message
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.session import SessionInfo, require_admin
from app.db.models import AdminUser, Organization, OrgNotificationSettings, SubscriptionPlan
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/notification-settings", tags=["notification-settings"])


# ── Pydantic schemas ────────────────────────────────────────────────────────────

class NotificationSettingsRead(BaseModel):
    organization_id: str
    teams_webhook_url: str | None
    teams_channel_name: str | None
    email_enabled: bool
    updated_at: datetime


class NotificationSettingsUpdate(BaseModel):
    teams_webhook_url: str | None = None
    teams_channel_name: str | None = None
    email_enabled: bool | None = None


class TestTeamsRequest(BaseModel):
    message: str = "Test message from Mastery Pulse notification system."


# ── helpers ─────────────────────────────────────────────────────────────────────

async def _get_org_and_plan(
    admin: AdminUser, db: AsyncSession
) -> tuple[Organization, SubscriptionPlan]:
    """Return (org, plan) for the admin's organization. 404 if org not found."""
    if admin.organization_id is None:
        raise HTTPException(status_code=403, detail="Admin has no associated organization")

    org = await db.get(Organization, admin.organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    plan = await db.get(SubscriptionPlan, org.plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")

    return org, plan


async def _require_teams_enabled(plan: SubscriptionPlan) -> None:
    """Raise 403 if the plan does not include Teams notifications."""
    if not plan.teams_notifications_enabled:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "enterprise_only",
                "message": "Teams notifications are only available on enterprise plans.",
            },
        )


async def _get_or_create_settings(
    org: Organization, db: AsyncSession
) -> OrgNotificationSettings:
    """Return existing settings or auto-create an empty row."""
    result = await db.execute(
        select(OrgNotificationSettings).where(
            OrgNotificationSettings.organization_id == org.id
        )
    )
    settings_row = result.scalar_one_or_none()
    if settings_row is None:
        settings_row = OrgNotificationSettings(
            organization_id=org.id,
            teams_webhook_url=None,
            teams_channel_name=None,
            email_enabled=False,
            updated_at=datetime.now(UTC),
        )
        db.add(settings_row)
        await db.flush()
    return settings_row


# ── Endpoints ───────────────────────────────────────────────────────────────────

@router.get("", response_model=NotificationSettingsRead)
async def get_notification_settings(
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_admin),
) -> NotificationSettingsRead:
    """Return the org's notification settings (auto-creates empty if not found)."""
    admin = await db.get(AdminUser, session.admin_user_id)
    if admin is None:
        raise HTTPException(status_code=404, detail="Admin not found")

    org, plan = await _get_org_and_plan(admin, db)

    if not plan.teams_notifications_enabled:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "enterprise_only",
                "message": "Notification settings are only available on enterprise plans.",
            },
        )

    settings_row = await _get_or_create_settings(org, db)
    await db.commit()
    return NotificationSettingsRead(
        organization_id=settings_row.organization_id,
        teams_webhook_url=settings_row.teams_webhook_url,
        teams_channel_name=settings_row.teams_channel_name,
        email_enabled=settings_row.email_enabled,
        updated_at=settings_row.updated_at,
    )


@router.put("", response_model=NotificationSettingsRead)
async def upsert_notification_settings(
    body: NotificationSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_admin),
) -> NotificationSettingsRead:
    """Upsert the org's notification settings."""
    admin = await db.get(AdminUser, session.admin_user_id)
    if admin is None:
        raise HTTPException(status_code=404, detail="Admin not found")

    org, plan = await _get_org_and_plan(admin, db)
    await _require_teams_enabled(plan)

    settings_row = await _get_or_create_settings(org, db)

    if body.teams_webhook_url is not None:
        settings_row.teams_webhook_url = body.teams_webhook_url
    if body.teams_channel_name is not None:
        settings_row.teams_channel_name = body.teams_channel_name
    if body.email_enabled is not None:
        settings_row.email_enabled = body.email_enabled

    settings_row.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(settings_row)

    return NotificationSettingsRead(
        organization_id=settings_row.organization_id,
        teams_webhook_url=settings_row.teams_webhook_url,
        teams_channel_name=settings_row.teams_channel_name,
        email_enabled=settings_row.email_enabled,
        updated_at=settings_row.updated_at,
    )


@router.post("/test-teams")
async def test_teams_webhook(
    body: TestTeamsRequest,
    db: AsyncSession = Depends(get_db),
    session: SessionInfo = Depends(require_admin),
) -> dict[str, object]:
    """Send a test message to the org's configured Teams webhook."""
    admin = await db.get(AdminUser, session.admin_user_id)
    if admin is None:
        raise HTTPException(status_code=404, detail="Admin not found")

    org, plan = await _get_org_and_plan(admin, db)
    await _require_teams_enabled(plan)

    result = await db.execute(
        select(OrgNotificationSettings).where(
            OrgNotificationSettings.organization_id == org.id
        )
    )
    settings_row = result.scalar_one_or_none()

    if settings_row is None or not settings_row.teams_webhook_url:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "teams_not_configured",
                "message": "No Teams webhook URL configured for this organization.",
            },
        )

    # Post to the webhook
    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "text": body.message,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(settings_row.teams_webhook_url, json=payload)
            if resp.status_code >= 400:
                return {"success": False, "error": f"Webhook returned HTTP {resp.status_code}"}
    except httpx.TimeoutException:
        return {"success": False, "error": "Request timed out after 10 seconds"}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Teams webhook test failed: %s", exc)
        return {"success": False, "error": str(exc)}

    return {"success": True}
