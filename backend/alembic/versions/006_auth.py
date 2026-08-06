"""Auth tables — Phase 5.2.

Covers: admin_users, sessions.

Revision ID: 006
Revises: 005
Create Date: 2026-08-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── admin_users ────────────────────────────────────────────────────────
    op.create_table(
        "admin_users",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(30), nullable=False, server_default="admin"),
        sa.Column(
            "must_change_password", sa.Boolean, nullable=False, server_default="true"
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('admin','leadership')",
            name="ck_admin_users_role",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_admin_users_email"),
    )
    op.create_index("ix_admin_users_email", "admin_users", ["email"])

    # ── sessions ───────────────────────────────────────────────────────────
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("identity_type", sa.String(20), nullable=False),
        sa.Column("practitioner_id", sa.String(36), nullable=True),
        sa.Column("admin_user_id", sa.String(36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "identity_type IN ('practitioner','admin')",
            name="ck_sessions_identity_type",
        ),
        sa.ForeignKeyConstraint(
            ["practitioner_id"], ["practitioners.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["admin_user_id"], ["admin_users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sessions_practitioner_id", "sessions", ["practitioner_id"])
    op.create_index("ix_sessions_admin_user_id", "sessions", ["admin_user_id"])

    # ── seed the starter admin account ─────────────────────────────────────
    # password = "welcome", bcrypt-hashed at cost 12. Must-change-password = true.
    # Generated with: bcrypt.hashpw(b"welcome", bcrypt.gensalt(12)).decode()
    op.execute(
        "INSERT INTO admin_users (id, email, first_name, password_hash, role, "
        "must_change_password) VALUES ("
        "'admin-seed-000000000000000000000000',"
        "'admin@example.com',"
        "'Admin',"
        # bcrypt hash of "welcome" — safe to store in source; never used in production
        "'$2b$12$bOVQaKq6FXQsi1.ml5yAmO5uo/ZzivRVBknHSJgixSnwCU3MIAzWm',"
        "'admin',"
        "'true'"
        ")"
    )


def downgrade() -> None:
    op.drop_table("sessions")
    op.drop_table("admin_users")
