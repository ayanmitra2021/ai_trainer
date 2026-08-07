"""Smart Nudge System — Phase 7.1.

Covers: nudge_categories table, mastery_history table,
        ALTER nudges to add campaign columns.

Revision ID: 008
Revises: 007
Create Date: 2026-08-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── nudge_categories ──────────────────────────────────────────────────────
    op.create_table(
        "nudge_categories",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("criteria", JSONB, nullable=False),
        sa.Column("is_custom", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("tone_hint", sa.String(500), nullable=True),
        sa.Column("estimated_reach", sa.Integer, nullable=True),
        sa.Column("created_by_admin_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_admin_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_nudge_categories_created_at", "nudge_categories", ["created_at"])

    # ── mastery_history ───────────────────────────────────────────────────────
    op.create_table(
        "mastery_history",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("practitioner_id", sa.String(36), nullable=False),
        sa.Column("skill_id", sa.String(36), nullable=False),
        sa.Column("mastery_score", sa.Numeric(4, 3), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["practitioner_id"], ["practitioners.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mastery_history_practitioner_id", "mastery_history", ["practitioner_id"])
    op.create_index("ix_mastery_history_skill_id", "mastery_history", ["skill_id"])
    op.create_index("ix_mastery_history_recorded_at", "mastery_history", ["recorded_at"])

    # ── alter nudges ──────────────────────────────────────────────────────────
    op.add_column("nudges", sa.Column("nudge_category_id", sa.String(36), nullable=True))
    op.add_column("nudges", sa.Column("subject", sa.Text, nullable=True))
    op.add_column("nudges", sa.Column("is_read", sa.Boolean, nullable=False, server_default="false"))
    op.add_column("nudges", sa.Column("read_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("nudges", sa.Column("created_by_admin_id", sa.String(36), nullable=True))
    op.create_foreign_key(
        "fk_nudges_nudge_category_id",
        "nudges", "nudge_categories",
        ["nudge_category_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_nudges_created_by_admin_id",
        "nudges", "admin_users",
        ["created_by_admin_id"], ["id"],
        ondelete="SET NULL",
    )
    # Drop old check constraint and recreate with 'campaign' added
    op.drop_constraint("ck_nudges_type", "nudges", type_="check")
    op.create_check_constraint(
        "ck_nudges_type",
        "nudges",
        "nudge_type IN ('gap_alert','encouragement','reminder','campaign')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_nudges_type", "nudges", type_="check")
    op.create_check_constraint(
        "ck_nudges_type",
        "nudges",
        "nudge_type IN ('gap_alert','encouragement','reminder')",
    )
    op.drop_constraint("fk_nudges_created_by_admin_id", "nudges", type_="foreignkey")
    op.drop_constraint("fk_nudges_nudge_category_id", "nudges", type_="foreignkey")
    op.drop_column("nudges", "created_by_admin_id")
    op.drop_column("nudges", "read_at")
    op.drop_column("nudges", "is_read")
    op.drop_column("nudges", "subject")
    op.drop_column("nudges", "nudge_category_id")
    op.drop_index("ix_mastery_history_recorded_at", "mastery_history")
    op.drop_index("ix_mastery_history_skill_id", "mastery_history")
    op.drop_index("ix_mastery_history_practitioner_id", "mastery_history")
    op.drop_table("mastery_history")
    op.drop_index("ix_nudge_categories_created_at", "nudge_categories")
    op.drop_table("nudge_categories")
