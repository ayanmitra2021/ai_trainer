"""Learning path tables — Phase 2.5.

Covers: learning_paths, learning_path_items.

Revision ID: 003
Revises: 002
Create Date: 2026-08-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── learning_paths ─────────────────────────────────────────────────────
    op.create_table(
        "learning_paths",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("practitioner_id", sa.String(36), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("workflow_run_id", sa.String(36), nullable=True),
        sa.CheckConstraint(
            "status IN ('draft','active','completed')",
            name="ck_learning_paths_status",
        ),
        sa.ForeignKeyConstraint(
            ["practitioner_id"], ["practitioners.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["workflow_run_id"], ["workflow_runs.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_learning_paths_practitioner_id", "learning_paths", ["practitioner_id"]
    )
    op.create_index(
        "ix_learning_paths_workflow_run_id", "learning_paths", ["workflow_run_id"]
    )

    # ── learning_path_items ────────────────────────────────────────────────
    op.create_table(
        "learning_path_items",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("learning_path_id", sa.String(36), nullable=False),
        sa.Column("skill_id", sa.String(36), nullable=False),
        sa.Column("sequence_order", sa.Integer, nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False, server_default="item_set"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("rationale", sa.Text, nullable=True),
        sa.CheckConstraint(
            "resource_type IN ('item_set','scenario_lab','external_reading')",
            name="ck_learning_path_items_resource_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending','in_progress','done')",
            name="ck_learning_path_items_status",
        ),
        sa.ForeignKeyConstraint(
            ["learning_path_id"], ["learning_paths.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_learning_path_items_learning_path_id",
        "learning_path_items",
        ["learning_path_id"],
    )
    op.create_index(
        "ix_learning_path_items_skill_id", "learning_path_items", ["skill_id"]
    )


def downgrade() -> None:
    op.drop_table("learning_path_items")
    op.drop_table("learning_paths")
