"""Add abandoned status + abandoned_reason / abandoned_at to mock_exam_sessions.

Revision ID: 022
Revises: 021
Create Date: 2026-08-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop constraint that lacks 'abandoned', then re-create with it included.
    op.drop_constraint("ck_mock_exam_sessions_status", "mock_exam_sessions")
    op.create_check_constraint(
        "ck_mock_exam_sessions_status",
        "mock_exam_sessions",
        "status IN ('generating','in_progress','paused','completed','failed','abandoned')",
    )

    # New columns for abandonment tracking
    op.add_column(
        "mock_exam_sessions",
        sa.Column("abandoned_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "mock_exam_sessions",
        sa.Column("abandoned_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("mock_exam_sessions", "abandoned_at")
    op.drop_column("mock_exam_sessions", "abandoned_reason")
    op.drop_constraint("ck_mock_exam_sessions_status", "mock_exam_sessions")
    op.create_check_constraint(
        "ck_mock_exam_sessions_status",
        "mock_exam_sessions",
        "status IN ('generating','in_progress','paused','completed','failed')",
    )
