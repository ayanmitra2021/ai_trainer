"""Phase 17.5 — learning_path_items: add quiz_status for background quiz generation tracking.

quiz_status tracks whether the background task has generated questions for each
skill in a learning path:
  pending — not yet attempted (default at path creation time)
  ready   — agent call succeeded; items are written to the items table
  failed  — all provider tiers exhausted; no items written; practitioner can retry

Revision ID: 018
Revises: 017
Create Date: 2026-08-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "learning_path_items",
        sa.Column(
            "quiz_status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
    )
    op.create_check_constraint(
        "ck_learning_path_items_quiz_status",
        "learning_path_items",
        "quiz_status IN ('pending','ready','failed')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_learning_path_items_quiz_status",
        "learning_path_items",
        type_="check",
    )
    op.drop_column("learning_path_items", "quiz_status")
