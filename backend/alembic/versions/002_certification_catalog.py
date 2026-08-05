"""Certification catalog — Phase 2.2 tables.

Covers: certification_providers, certifications, certification_skills,
practitioner_certification_goals, certification_advisor_responses.

Revision ID: 002
Revises: 001
Create Date: 2026-08-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── certification_providers ────────────────────────────────────────────
    op.create_table(
        "certification_providers",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_certification_providers_name"),
    )
    op.create_index("ix_certification_providers_name", "certification_providers", ["name"])

    # ── certifications ─────────────────────────────────────────────────────
    op.create_table(
        "certifications",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("provider_id", sa.String(36), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("level", sa.String(50), nullable=False),
        sa.Column("requires_coding_background", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("typical_audience", sa.Text, nullable=True),
        sa.Column("focus_area", sa.Text, nullable=True),
        sa.Column("exam_format", sa.Text, nullable=True),
        sa.Column("eligibility_notes", sa.Text, nullable=True),
        sa.Column("external_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_verified_at", sa.Date, nullable=True),
        sa.CheckConstraint(
            "level IN ('foundational','associate','professional','specialty','expert')",
            name="ck_certifications_level",
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"], ["certification_providers.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_certifications_code"),
    )
    op.create_index("ix_certifications_code", "certifications", ["code"])
    op.create_index("ix_certifications_provider_id", "certifications", ["provider_id"])

    # ── certification_skills ───────────────────────────────────────────────
    op.create_table(
        "certification_skills",
        sa.Column("certification_id", sa.String(36), nullable=False),
        sa.Column("skill_id", sa.String(36), nullable=False),
        sa.Column("weight", sa.Numeric(4, 3), nullable=False, server_default="1.0"),
        sa.CheckConstraint(
            "weight >= 0 AND weight <= 1",
            name="ck_certification_skills_weight",
        ),
        sa.ForeignKeyConstraint(
            ["certification_id"], ["certifications.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("certification_id", "skill_id"),
    )

    # ── practitioner_certification_goals ───────────────────────────────────
    op.create_table(
        "practitioner_certification_goals",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("practitioner_id", sa.String(36), nullable=False),
        sa.Column("certification_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="recommended"),
        sa.Column(
            "recommended_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("selected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("achieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('recommended','selected','in_progress','achieved','abandoned')",
            name="ck_practitioner_cert_goals_status",
        ),
        sa.ForeignKeyConstraint(
            ["practitioner_id"], ["practitioners.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["certification_id"], ["certifications.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_practitioner_cert_goals_practitioner_id",
        "practitioner_certification_goals",
        ["practitioner_id"],
    )
    op.create_index(
        "ix_practitioner_cert_goals_certification_id",
        "practitioner_certification_goals",
        ["certification_id"],
    )

    # ── certification_advisor_responses ────────────────────────────────────
    op.create_table(
        "certification_advisor_responses",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("practitioner_id", sa.String(36), nullable=False),
        sa.Column("responses", sa.JSON, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["practitioner_id"], ["practitioners.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cert_advisor_responses_practitioner_id",
        "certification_advisor_responses",
        ["practitioner_id"],
    )


def downgrade() -> None:
    op.drop_table("certification_advisor_responses")
    op.drop_table("practitioner_certification_goals")
    op.drop_table("certification_skills")
    op.drop_table("certifications")
    op.drop_table("certification_providers")
