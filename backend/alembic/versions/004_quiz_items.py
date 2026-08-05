"""Quiz items and attempts — Phase 2.6 / 2.7.

Covers: items, attempts.

Revision ID: 004
Revises: 003
Create Date: 2026-08-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── items ──────────────────────────────────────────────────────────────
    op.create_table(
        "items",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("skill_id", sa.String(36), nullable=False),
        sa.Column("item_type", sa.String(20), nullable=False),
        sa.Column("prompt", sa.Text, nullable=False),
        sa.Column("answer_key", sa.JSON, nullable=False),
        sa.Column("trap_explanation", sa.Text, nullable=True),
        sa.Column("difficulty", sa.Numeric(4, 3), nullable=False, server_default="0.5"),
        sa.Column("calibration_stats", sa.JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "item_type IN ('mcq','free_text','scenario')",
            name="ck_items_item_type",
        ),
        sa.CheckConstraint(
            "difficulty >= 0 AND difficulty <= 1",
            name="ck_items_difficulty",
        ),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_items_skill_id", "items", ["skill_id"])

    # ── attempts ───────────────────────────────────────────────────────────
    op.create_table(
        "attempts",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("practitioner_id", sa.String(36), nullable=False),
        sa.Column("item_id", sa.String(36), nullable=False),
        sa.Column("response", sa.JSON, nullable=False),
        sa.Column("score", sa.Numeric(4, 3), nullable=False),
        sa.Column("grader_rationale", sa.Text, nullable=False),
        sa.Column("is_trap_selected", sa.Boolean, nullable=True),
        sa.Column(
            "attempted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "score >= 0 AND score <= 1",
            name="ck_attempts_score",
        ),
        sa.ForeignKeyConstraint(
            ["practitioner_id"], ["practitioners.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_attempts_practitioner_id", "attempts", ["practitioner_id"])
    op.create_index("ix_attempts_item_id", "attempts", ["item_id"])


def downgrade() -> None:
    op.drop_table("attempts")
    op.drop_table("items")
