"""Phase 11 — Mock Exam feature.

Schema additions:
1. ``certifications``: three new nullable exam-config columns
   (exam_question_count, exam_duration_minutes, exam_passing_score_pct)
2. ``mock_exam_sessions`` table — one per exam sitting, with pause/resume support
3. ``mock_exam_questions`` table — individual MCQ rows for each session
4. ``skill_profile_events``.source constraint expanded to include 'mock_exam'

Revision ID: 016
Revises: 015
Create Date: 2026-08-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── certifications: add exam-config columns ───────────────────────────────
    op.add_column(
        "certifications",
        sa.Column("exam_question_count", sa.Integer, nullable=True),
    )
    op.add_column(
        "certifications",
        sa.Column("exam_duration_minutes", sa.Integer, nullable=True),
    )
    op.add_column(
        "certifications",
        sa.Column("exam_passing_score_pct", sa.Numeric(5, 2), nullable=True),
    )

    # ── mock_exam_sessions ────────────────────────────────────────────────────
    op.create_table(
        "mock_exam_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "practitioner_id",
            sa.String(36),
            sa.ForeignKey("practitioners.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "certification_id",
            sa.String(36),
            sa.ForeignKey("certifications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="in_progress",
        ),
        sa.Column(
            "time_elapsed_seconds",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "last_resumed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("score", sa.Numeric(4, 3), nullable=True),
        sa.Column("correct_count", sa.Integer, nullable=True),
        sa.Column("total_count", sa.Integer, nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "status IN ('in_progress','paused','completed')",
            name="ck_mock_exam_sessions_status",
        ),
    )
    op.create_index(
        "ix_mock_exam_sessions_practitioner_id",
        "mock_exam_sessions",
        ["practitioner_id"],
    )
    op.create_index(
        "ix_mock_exam_sessions_certification_id",
        "mock_exam_sessions",
        ["certification_id"],
    )

    # ── mock_exam_questions ───────────────────────────────────────────────────
    op.create_table(
        "mock_exam_questions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("mock_exam_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence_order", sa.Integer, nullable=False),
        sa.Column("certification_domain_name", sa.String(200), nullable=True),
        sa.Column("skill_name", sa.String(200), nullable=True),
        sa.Column("prompt", sa.Text, nullable=False),
        sa.Column("answer_key", sa.JSON, nullable=False),
        sa.Column("trap_explanation", sa.Text, nullable=True),
        sa.Column("difficulty", sa.Numeric(4, 3), nullable=False),
        sa.Column("response", sa.JSON, nullable=True),
        sa.Column("score", sa.Numeric(4, 3), nullable=True),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_mock_exam_questions_session_id",
        "mock_exam_questions",
        ["session_id"],
    )

    # ── expand skill_profile_events.source check constraint ───────────────────
    # Drop the old constraint and recreate with 'mock_exam' included.
    op.drop_constraint(
        "ck_skill_profile_events_source",
        "skill_profile_events",
        type_="check",
    )
    op.create_check_constraint(
        "ck_skill_profile_events_source",
        "skill_profile_events",
        "source IN ('certification','self_assessment','quiz_attempt','project_history','mock_exam')",
    )


def downgrade() -> None:
    # Restore original source constraint
    op.drop_constraint(
        "ck_skill_profile_events_source",
        "skill_profile_events",
        type_="check",
    )
    op.create_check_constraint(
        "ck_skill_profile_events_source",
        "skill_profile_events",
        "source IN ('certification','self_assessment','quiz_attempt','project_history')",
    )

    op.drop_index("ix_mock_exam_questions_session_id", table_name="mock_exam_questions")
    op.drop_table("mock_exam_questions")

    op.drop_index("ix_mock_exam_sessions_certification_id", table_name="mock_exam_sessions")
    op.drop_index("ix_mock_exam_sessions_practitioner_id", table_name="mock_exam_sessions")
    op.drop_table("mock_exam_sessions")

    with op.batch_alter_table("certifications") as batch_op:
        batch_op.drop_column("exam_passing_score_pct")
        batch_op.drop_column("exam_duration_minutes")
        batch_op.drop_column("exam_question_count")
