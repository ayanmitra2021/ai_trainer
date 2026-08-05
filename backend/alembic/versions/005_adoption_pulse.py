"""Adoption Pulse tables — Phase 3.

Covers: usage_events, correlation_snapshots, nudges, rollups.

Revision ID: 005
Revises: 004
Create Date: 2026-08-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── workflow_runs status: extend to allow 'partial' (nightly_pulse) ───
    # SQLite (tests) inherits this from the updated model via create_all().
    # Postgres requires an explicit constraint swap.
    connection = op.get_bind()
    if connection.dialect.name == "postgresql":
        op.execute(
            "ALTER TABLE workflow_runs "
            "DROP CONSTRAINT IF EXISTS ck_workflow_runs_status"
        )
        op.execute(
            "ALTER TABLE workflow_runs ADD CONSTRAINT ck_workflow_runs_status "
            "CHECK (status IN ('running','completed','failed','partial'))"
        )

    # ── usage_events (append-only) ─────────────────────────────────────────
    op.create_table(
        "usage_events",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("practitioner_id", sa.String(36), nullable=False),
        sa.Column("signal_type", sa.String(50), nullable=False),
        sa.Column("skill_id", sa.String(36), nullable=True),
        sa.Column("raw_ref", sa.String(500), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "signal_type IN ('claude_code_session','git_commit','other')",
            name="ck_usage_events_signal_type",
        ),
        sa.ForeignKeyConstraint(
            ["practitioner_id"], ["practitioners.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["skill_id"], ["skills.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_usage_events_practitioner_id", "usage_events", ["practitioner_id"])
    op.create_index("ix_usage_events_skill_id", "usage_events", ["skill_id"])
    op.create_index("ix_usage_events_occurred_at", "usage_events", ["occurred_at"])

    # ── correlation_snapshots (derived, append-only history) ───────────────
    op.create_table(
        "correlation_snapshots",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("practitioner_id", sa.String(36), nullable=False),
        sa.Column("skill_id", sa.String(36), nullable=False),
        sa.Column("trained_score", sa.Numeric(4, 3), nullable=False),
        sa.Column("adoption_score", sa.Numeric(4, 3), nullable=False),
        sa.Column("gap_score", sa.Numeric(4, 3), nullable=False),
        sa.Column("has_adoption_gap", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("reasoning", sa.Text, nullable=True),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "trained_score >= 0 AND trained_score <= 1",
            name="ck_correlation_trained_score",
        ),
        sa.CheckConstraint(
            "adoption_score >= 0 AND adoption_score <= 1",
            name="ck_correlation_adoption_score",
        ),
        sa.CheckConstraint(
            "gap_score >= 0 AND gap_score <= 1",
            name="ck_correlation_gap_score",
        ),
        sa.ForeignKeyConstraint(
            ["practitioner_id"], ["practitioners.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["skill_id"], ["skills.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_correlation_snapshots_practitioner_id",
        "correlation_snapshots",
        ["practitioner_id"],
    )
    op.create_index(
        "ix_correlation_snapshots_skill_id", "correlation_snapshots", ["skill_id"]
    )

    # ── nudges ─────────────────────────────────────────────────────────────
    op.create_table(
        "nudges",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("practitioner_id", sa.String(36), nullable=False),
        sa.Column("nudge_type", sa.String(30), nullable=False),
        sa.Column("channel", sa.String(30), nullable=False, server_default="in_app"),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="drafted"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("composer_reasoning", sa.Text, nullable=True),
        sa.CheckConstraint(
            "nudge_type IN ('gap_alert','encouragement','reminder')",
            name="ck_nudges_type",
        ),
        sa.CheckConstraint(
            "channel IN ('email','in_app')",
            name="ck_nudges_channel",
        ),
        sa.CheckConstraint(
            "status IN ('drafted','approved','sent')",
            name="ck_nudges_status",
        ),
        sa.ForeignKeyConstraint(
            ["practitioner_id"], ["practitioners.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_nudges_practitioner_id", "nudges", ["practitioner_id"])

    # ── rollups ────────────────────────────────────────────────────────────
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


def downgrade() -> None:
    op.drop_table("rollups")
    op.drop_table("nudges")
    op.drop_table("correlation_snapshots")
    op.drop_table("usage_events")
