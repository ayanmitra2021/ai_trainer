"""Add 'generating' and 'failed' to mock_exam_sessions.status check constraint.

Revision ID: 020
Revises: 019
Create Date: 2026-08-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old constraint, add new one with 'generating' and 'failed' included.
    # Postgres requires DROP + ADD; ALTER TABLE … ALTER CONSTRAINT is not supported.
    op.drop_constraint("ck_mock_exam_sessions_status", "mock_exam_sessions")
    op.create_check_constraint(
        "ck_mock_exam_sessions_status",
        "mock_exam_sessions",
        "status IN ('generating','in_progress','paused','completed','failed')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_mock_exam_sessions_status", "mock_exam_sessions")
    op.create_check_constraint(
        "ck_mock_exam_sessions_status",
        "mock_exam_sessions",
        "status IN ('in_progress','paused','completed')",
    )
