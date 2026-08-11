"""Phase 9.1 — Remove rollups table and nightly_pulse workflow.

The aggregated leadership rollup reports and the fully-automated nightly nudge
pipeline have been removed from the product. The ``rollups`` table served only
the Rollup Reporter agent and the ``/rollups`` API — both of which are now gone.

Notes:
  - No foreign keys from any other table pointed at ``rollups``; the drop is safe.
  - The ``workflow_runs.workflow_name`` column is VARCHAR(100) with no DB-level
    enum constraint; the "nightly_pulse" string value is left as a legacy
    historical value in existing rows (no migration needed for that column).
    The active code no longer creates new rows with that name.
  - The ``rollups`` index on ``scope_ref`` is dropped automatically with the table.

Revision ID: 009
Revises: 008
Create Date: 2026-08-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the rollups table. No FK constraints from other tables reference it.
    op.drop_table("rollups")


def downgrade() -> None:
    # Recreate rollups table to restore the pre-9.1 state.
    op.create_table(
        "rollups",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("scope", sa.String(30), nullable=False),
        sa.Column("scope_ref", sa.String(255), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metrics", sa.JSON, nullable=True),
        sa.Column("narrative", sa.Text, nullable=True),
        sa.Column(
            "min_cohort_size_met",
            sa.Boolean,
            nullable=False,
            server_default="false",
        ),
        sa.Column("min_cohort_size", sa.Integer, nullable=False, server_default="5"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "scope IN ('team','practice')",
            name="ck_rollups_scope",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rollups_scope_ref", "rollups", ["scope_ref"])
