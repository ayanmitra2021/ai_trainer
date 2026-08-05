"""Initial schema — Phase 0 tables.

Covers: practitioners, skills, skill_profile_events, skill_profile_snapshots,
workflow_runs, agent_runs.

Revision ID: 001
Revises: (none — first migration)
Create Date: 2026-08-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── practitioners ─────────────────────────────────────────────────────
    op.create_table(
        "practitioners",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", sa.String(255), nullable=True),
        sa.Column("practice", sa.String(255), nullable=True),
        sa.Column("seniority_level", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_practitioners_email", "practitioners", ["email"], unique=True)

    # ── skills ────────────────────────────────────────────────────────────
    op.create_table(
        "skills",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(255), nullable=False),
        sa.Column("parent_skill_id", sa.String(36), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.ForeignKeyConstraint(
            ["parent_skill_id"],
            ["skills.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_skills_name", "skills", ["name"])

    # ── skill_profile_events ──────────────────────────────────────────────
    op.create_table(
        "skill_profile_events",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("practitioner_id", sa.String(36), nullable=False),
        sa.Column("skill_id", sa.String(36), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("signal_strength", sa.Numeric(4, 3), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", sa.JSON, nullable=True),
        sa.CheckConstraint(
            "source IN ('certification','self_assessment','quiz_attempt','project_history')",
            name="ck_skill_profile_events_source",
        ),
        sa.CheckConstraint(
            "signal_strength >= 0 AND signal_strength <= 1",
            name="ck_skill_profile_events_signal_strength",
        ),
        sa.ForeignKeyConstraint(
            ["practitioner_id"], ["practitioners.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_skill_profile_events_practitioner_id",
        "skill_profile_events",
        ["practitioner_id"],
    )
    op.create_index(
        "ix_skill_profile_events_skill_id",
        "skill_profile_events",
        ["skill_id"],
    )

    # ── skill_profile_snapshots ───────────────────────────────────────────
    op.create_table(
        "skill_profile_snapshots",
        sa.Column("practitioner_id", sa.String(36), nullable=False),
        sa.Column("skill_id", sa.String(36), nullable=False),
        sa.Column("mastery_score", sa.Numeric(4, 3), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("last_computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "mastery_score >= 0 AND mastery_score <= 1",
            name="ck_skill_profile_snapshots_mastery",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_skill_profile_snapshots_confidence",
        ),
        sa.ForeignKeyConstraint(
            ["practitioner_id"], ["practitioners.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("practitioner_id", "skill_id"),
    )

    # ── workflow_runs ──────────────────────────────────────────────────────
    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("workflow_name", sa.String(100), nullable=False),
        sa.Column("triggered_by", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('running','completed','failed')",
            name="ck_workflow_runs_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_runs_workflow_name", "workflow_runs", ["workflow_name"])

    # ── agent_runs ─────────────────────────────────────────────────────────
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("workflow_run_id", sa.String(36), nullable=True),
        sa.Column("input", sa.JSON, nullable=True),
        sa.Column("output", sa.JSON, nullable=True),
        sa.Column("model_used", sa.String(100), nullable=True),
        sa.Column("tokens_input", sa.Integer, nullable=True),
        sa.Column("tokens_output", sa.Integer, nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="success"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('success','error')",
            name="ck_agent_runs_status",
        ),
        sa.ForeignKeyConstraint(
            ["workflow_run_id"], ["workflow_runs.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_runs_agent_name", "agent_runs", ["agent_name"])
    op.create_index("ix_agent_runs_workflow_run_id", "agent_runs", ["workflow_run_id"])


def downgrade() -> None:
    # Drop in reverse dependency order.
    op.drop_table("agent_runs")
    op.drop_table("workflow_runs")
    op.drop_table("skill_profile_snapshots")
    op.drop_table("skill_profile_events")
    op.drop_table("skills")
    op.drop_table("practitioners")
