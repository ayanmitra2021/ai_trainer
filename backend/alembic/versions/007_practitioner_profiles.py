"""Practitioner profiles — Phase 6.1.

Covers: practitioner_profiles, profile_skill_assessments.
Also adds profile_id FK column to certification_advisor_responses and
practitioner_certification_goals.

Revision ID: 007
Revises: 006
Create Date: 2026-08-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── practitioner_profiles ──────────────────────────────────────────────
    op.create_table(
        "practitioner_profiles",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("practitioner_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("certification_id", sa.String(36), nullable=True),
        sa.Column("questionnaire_snapshot", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["practitioner_id"], ["practitioners.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["certification_id"], ["certifications.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_practitioner_profiles_practitioner_id",
        "practitioner_profiles",
        ["practitioner_id"],
    )

    # ── profile_skill_assessments ──────────────────────────────────────────
    op.create_table(
        "profile_skill_assessments",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("profile_id", sa.String(36), nullable=False),
        sa.Column("skill_id", sa.String(36), nullable=False),
        sa.Column("signal_strength", sa.Numeric(4, 3), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["practitioner_profiles.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["skill_id"], ["skills.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "profile_id", "skill_id", name="uq_profile_skill_assessments"
        ),
        sa.CheckConstraint(
            "signal_strength >= 0 AND signal_strength <= 1",
            name="ck_profile_skill_assessments_signal_strength",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_profile_skill_assessments_profile_id",
        "profile_skill_assessments",
        ["profile_id"],
    )
    op.create_index(
        "ix_profile_skill_assessments_skill_id",
        "profile_skill_assessments",
        ["skill_id"],
    )

    # ── ADD profile_id to certification_advisor_responses ──────────────────
    op.add_column(
        "certification_advisor_responses",
        sa.Column("profile_id", sa.String(36), nullable=True),
    )
    op.create_foreign_key(
        "fk_cert_advisor_responses_profile_id",
        "certification_advisor_responses",
        "practitioner_profiles",
        ["profile_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # ── ADD profile_id to practitioner_certification_goals ─────────────────
    op.add_column(
        "practitioner_certification_goals",
        sa.Column("profile_id", sa.String(36), nullable=True),
    )
    op.create_foreign_key(
        "fk_practitioner_cert_goals_profile_id",
        "practitioner_certification_goals",
        "practitioner_profiles",
        ["profile_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # Drop FK constraints and columns first, then tables
    op.drop_constraint(
        "fk_practitioner_cert_goals_profile_id",
        "practitioner_certification_goals",
        type_="foreignkey",
    )
    op.drop_column("practitioner_certification_goals", "profile_id")

    op.drop_constraint(
        "fk_cert_advisor_responses_profile_id",
        "certification_advisor_responses",
        type_="foreignkey",
    )
    op.drop_column("certification_advisor_responses", "profile_id")

    op.drop_index(
        "ix_profile_skill_assessments_skill_id",
        table_name="profile_skill_assessments",
    )
    op.drop_index(
        "ix_profile_skill_assessments_profile_id",
        table_name="profile_skill_assessments",
    )
    op.drop_table("profile_skill_assessments")

    op.drop_index(
        "ix_practitioner_profiles_practitioner_id",
        table_name="practitioner_profiles",
    )
    op.drop_table("practitioner_profiles")
