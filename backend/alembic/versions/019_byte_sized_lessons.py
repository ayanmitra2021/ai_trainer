"""Phase 18.1 — byte_sized_lessons and lesson_reads tables.

byte_sized_lessons: AI-generated micro-content per skill gap, one per skill per path generation.
lesson_reads: tracks when a practitioner opens and closes a lesson modal.

Revision ID: 020
Revises: 019
Create Date: 2026-08-18
"""

from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from alembic import op

revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "byte_sized_lessons",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("practitioner_id", sa.String(36), sa.ForeignKey("practitioners.id", ondelete="CASCADE"), nullable=False),
        sa.Column("learning_path_id", sa.String(36), sa.ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_id", sa.String(36), sa.ForeignKey("skills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_name", sa.Text, nullable=False),
        sa.Column("gap_pct", sa.Float, nullable=False),
        sa.Column("target_pct", sa.Float, nullable=False, server_default="0.85"),
        sa.Column("what_missing", sa.Text, nullable=True),
        sa.Column("content_md", sa.Text, nullable=True),
        sa.Column("external_links", JSONB, nullable=True),
        sa.Column("estimated_read_minutes", sa.SmallInteger, nullable=True),
        sa.Column("path_generation_seq", sa.Integer, nullable=False),
        sa.Column("generation_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_check_constraint(
        "ck_byte_sized_lessons_generation_status",
        "byte_sized_lessons",
        "generation_status IN ('pending','ready','failed')",
    )
    op.create_index("ix_byte_sized_lessons_practitioner_id", "byte_sized_lessons", ["practitioner_id"])
    op.create_index("ix_byte_sized_lessons_learning_path_id", "byte_sized_lessons", ["learning_path_id"])

    op.create_table(
        "lesson_reads",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("lesson_id", sa.String(36), sa.ForeignKey("byte_sized_lessons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("practitioner_id", sa.String(36), sa.ForeignKey("practitioners.id", ondelete="CASCADE"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_seconds", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_lesson_reads_lesson_id", "lesson_reads", ["lesson_id"])


def downgrade() -> None:
    op.drop_table("lesson_reads")
    op.drop_constraint("ck_byte_sized_lessons_generation_status", "byte_sized_lessons", type_="check")
    op.drop_table("byte_sized_lessons")
