"""Multi-tenant schema foundation — Phase 22

Revision ID: 024
Revises: 023
Create Date: 2026-08-20

Adds: subscription_plans, organizations, org_enrollment_codes, product_admin_users,
org_notification_settings tables. Adds organization_id to practitioners + admin_users,
deleted_at to practitioner_profiles, product_admin_user_id to sessions.
Updates sessions.identity_type check constraint.

Backfills existing practitioners and admin_users into a seeded Deloitte Consulting org.

To apply: alembic upgrade head
"""

from __future__ import annotations

import secrets
import uuid

import bcrypt
import sqlalchemy as sa
from alembic import op

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None

# ── Well-known fixed IDs ────────────────────────────────────────────────────────
ENTERPRISE_UNLIMITED_PLAN_ID = "00000000-0000-0000-0000-000000000001"
FREE_PLAN_ID = "00000000-0000-0000-0000-000000000002"
PAID_PLAN_ID = "00000000-0000-0000-0000-000000000003"
ENTERPRISE_100_PLAN_ID = "00000000-0000-0000-0000-000000000004"
ENTERPRISE_1000_PLAN_ID = "00000000-0000-0000-0000-000000000005"
DELOITTE_ORG_ID = "00000000-0000-0000-0000-000000000010"
FREE_TIER_ORG_ID = "00000000-0000-0000-0000-000000000011"
DEFAULT_PRODUCT_ADMIN_ID = "00000000-0000-0000-0000-000000000020"

_NOW = sa.text("now()")


def _gen_code() -> str:
    """Generate a 16-character uppercase hex enrollment code."""
    return secrets.token_hex(8).upper()


def upgrade() -> None:
    # ── 1. subscription_plans ──────────────────────────────────────────────────
    op.create_table(
        "subscription_plans",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("tier", sa.String(20), nullable=False),
        sa.Column("max_profiles_per_practitioner", sa.Integer, nullable=False),
        sa.Column("max_learning_paths", sa.Integer, nullable=False),
        sa.Column("max_mock_exams_per_profile", sa.Integer, nullable=False),
        sa.Column("max_practitioners_per_org", sa.Integer, nullable=False),
        sa.Column("allow_cert_recycling", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("nudges_enabled", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("teams_notifications_enabled", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=_NOW),
        sa.CheckConstraint("tier IN ('free','paid','enterprise')", name="ck_subscription_plans_tier"),
    )

    # Seed 5 plans
    plans_table = sa.table(
        "subscription_plans",
        sa.column("id", sa.String),
        sa.column("name", sa.Text),
        sa.column("tier", sa.String),
        sa.column("max_profiles_per_practitioner", sa.Integer),
        sa.column("max_learning_paths", sa.Integer),
        sa.column("max_mock_exams_per_profile", sa.Integer),
        sa.column("max_practitioners_per_org", sa.Integer),
        sa.column("allow_cert_recycling", sa.Boolean),
        sa.column("nudges_enabled", sa.Boolean),
        sa.column("teams_notifications_enabled", sa.Boolean),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(plans_table, [
        {
            "id": ENTERPRISE_UNLIMITED_PLAN_ID,
            "name": "Enterprise Unlimited",
            "tier": "enterprise",
            "max_profiles_per_practitioner": -1,
            "max_learning_paths": -1,
            "max_mock_exams_per_profile": -1,
            "max_practitioners_per_org": -1,
            "allow_cert_recycling": True,
            "nudges_enabled": True,
            "teams_notifications_enabled": True,
            "is_active": True,
        },
        {
            "id": FREE_PLAN_ID,
            "name": "Free",
            "tier": "free",
            "max_profiles_per_practitioner": 2,
            "max_learning_paths": 2,
            "max_mock_exams_per_profile": 2,
            "max_practitioners_per_org": -1,
            "allow_cert_recycling": False,
            "nudges_enabled": False,
            "teams_notifications_enabled": False,
            "is_active": True,
        },
        {
            "id": PAID_PLAN_ID,
            "name": "Paid",
            "tier": "paid",
            "max_profiles_per_practitioner": 5,
            "max_learning_paths": 10,
            "max_mock_exams_per_profile": 10,
            "max_practitioners_per_org": -1,
            "allow_cert_recycling": True,
            "nudges_enabled": False,
            "teams_notifications_enabled": False,
            "is_active": True,
        },
        {
            "id": ENTERPRISE_100_PLAN_ID,
            "name": "Enterprise 100",
            "tier": "enterprise",
            "max_profiles_per_practitioner": -1,
            "max_learning_paths": -1,
            "max_mock_exams_per_profile": -1,
            "max_practitioners_per_org": 100,
            "allow_cert_recycling": True,
            "nudges_enabled": True,
            "teams_notifications_enabled": True,
            "is_active": True,
        },
        {
            "id": ENTERPRISE_1000_PLAN_ID,
            "name": "Enterprise 1000",
            "tier": "enterprise",
            "max_profiles_per_practitioner": -1,
            "max_learning_paths": -1,
            "max_mock_exams_per_profile": -1,
            "max_practitioners_per_org": 1000,
            "allow_cert_recycling": True,
            "nudges_enabled": True,
            "teams_notifications_enabled": True,
            "is_active": True,
        },
    ])

    # ── 2. organizations ───────────────────────────────────────────────────────
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column(
            "plan_id", sa.String(36),
            sa.ForeignKey("subscription_plans.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("billing_email", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=_NOW),
    )

    orgs_table = sa.table(
        "organizations",
        sa.column("id", sa.String),
        sa.column("name", sa.Text),
        sa.column("plan_id", sa.String),
        sa.column("billing_email", sa.Text),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(orgs_table, [
        {
            "id": DELOITTE_ORG_ID,
            "name": "Deloitte Consulting",
            "plan_id": ENTERPRISE_UNLIMITED_PLAN_ID,
            "billing_email": "masteryplatform@deloitte.com",
            "is_active": True,
        },
        {
            "id": FREE_TIER_ORG_ID,
            "name": "Free Tier",
            "plan_id": FREE_PLAN_ID,
            "billing_email": None,
            "is_active": True,
        },
    ])

    # ── 3. org_enrollment_codes ────────────────────────────────────────────────
    op.create_table(
        "org_enrollment_codes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "organization_id", sa.String(36),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("code", sa.String(16), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_NOW),
        sa.CheckConstraint("char_length(code) = 16", name="ck_org_enrollment_codes_length"),
    )
    # Partial unique index: one active code per org
    op.create_index(
        "uq_org_enrollment_codes_active_per_org",
        "org_enrollment_codes",
        ["organization_id"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )

    codes_table = sa.table(
        "org_enrollment_codes",
        sa.column("id", sa.String),
        sa.column("organization_id", sa.String),
        sa.column("code", sa.String),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(codes_table, [
        {
            "id": str(uuid.uuid4()),
            "organization_id": DELOITTE_ORG_ID,
            "code": _gen_code(),
            "is_active": True,
        },
        {
            "id": str(uuid.uuid4()),
            "organization_id": FREE_TIER_ORG_ID,
            "code": _gen_code(),
            "is_active": True,
        },
    ])

    # ── 4. product_admin_users ─────────────────────────────────────────────────
    op.create_table(
        "product_admin_users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("must_change_password", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_NOW),
    )

    # Seed one product admin with temporary password "Welcome1!"
    _temp_pw_hash = bcrypt.hashpw(b"Welcome1!", bcrypt.gensalt()).decode()
    prod_admin_table = sa.table(
        "product_admin_users",
        sa.column("id", sa.String),
        sa.column("email", sa.String),
        sa.column("password_hash", sa.Text),
        sa.column("first_name", sa.String),
        sa.column("must_change_password", sa.Boolean),
    )
    op.bulk_insert(prod_admin_table, [
        {
            "id": DEFAULT_PRODUCT_ADMIN_ID,
            "email": "product@mastery-pulse.io",
            "password_hash": _temp_pw_hash,
            "first_name": "Platform",
            "must_change_password": True,
        },
    ])

    # ── 5. org_notification_settings ──────────────────────────────────────────
    op.create_table(
        "org_notification_settings",
        sa.Column(
            "organization_id", sa.String(36),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("teams_webhook_url", sa.Text, nullable=True),
        sa.Column("teams_channel_name", sa.Text, nullable=True),
        sa.Column("email_enabled", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=_NOW),
    )

    # ── 6. practitioners.organization_id ──────────────────────────────────────
    op.add_column(
        "practitioners",
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_practitioners_organization_id", "practitioners", ["organization_id"])
    # Backfill existing practitioners into Deloitte org
    op.execute(
        sa.text("UPDATE practitioners SET organization_id = :org_id").bindparams(
            org_id=DELOITTE_ORG_ID
        )
    )

    # ── 7. admin_users.organization_id ────────────────────────────────────────
    op.add_column(
        "admin_users",
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_admin_users_organization_id", "admin_users", ["organization_id"])
    # Backfill existing admin_users into Deloitte org
    op.execute(
        sa.text("UPDATE admin_users SET organization_id = :org_id").bindparams(
            org_id=DELOITTE_ORG_ID
        )
    )

    # ── 8. practitioner_profiles.deleted_at ───────────────────────────────────
    op.add_column(
        "practitioner_profiles",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── 9. sessions.product_admin_user_id ─────────────────────────────────────
    op.add_column(
        "sessions",
        sa.Column(
            "product_admin_user_id",
            sa.String(36),
            sa.ForeignKey("product_admin_users.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index("ix_sessions_product_admin_user_id", "sessions", ["product_admin_user_id"])

    # ── 10. sessions.identity_type check constraint ────────────────────────────
    # Drop the old constraint (Postgres-specific name from migration 005)
    op.drop_constraint("ck_sessions_identity_type", "sessions", type_="check")
    op.create_check_constraint(
        "ck_sessions_identity_type",
        "sessions",
        "identity_type IN ('practitioner','admin','product_admin')",
    )


def downgrade() -> None:
    # Restore old identity_type constraint
    op.drop_constraint("ck_sessions_identity_type", "sessions", type_="check")
    op.create_check_constraint(
        "ck_sessions_identity_type",
        "sessions",
        "identity_type IN ('practitioner','admin')",
    )

    op.drop_index("ix_sessions_product_admin_user_id", table_name="sessions")
    op.drop_column("sessions", "product_admin_user_id")

    op.drop_column("practitioner_profiles", "deleted_at")

    op.drop_index("ix_admin_users_organization_id", table_name="admin_users")
    op.drop_column("admin_users", "organization_id")

    op.drop_index("ix_practitioners_organization_id", table_name="practitioners")
    op.drop_column("practitioners", "organization_id")

    op.drop_table("org_notification_settings")

    op.drop_index("uq_org_enrollment_codes_active_per_org", table_name="org_enrollment_codes")
    op.drop_table("org_enrollment_codes")

    op.drop_table("product_admin_users")
    op.drop_table("organizations")
    op.drop_table("subscription_plans")
