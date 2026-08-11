"""Phase 10.1 — Certification exam domains data model.

Adds four schema changes:

1. ``certification_domains`` — the official exam-domain breakdown for each
   active certification (name, description, weight_pct, sequence_order).

2. ``certification_domain_scores`` — per-practitioner, per-domain readiness
   scores.  Starts as a ``self_assessment_estimate`` at profile-lock time
   (written by the Domain Scorer Agent in Step 10.2); becomes ``quiz_derived``
   once the practitioner submits cert-evaluated quiz answers.

3. ``items.certification_domain_id`` — nullable FK to certification_domains;
   NULL on legacy items, non-NULL on all items written after Step 10.3.

4. ``items.is_cert_evaluated`` — boolean flag (default false).  True means
   answering this item correctly moves the practitioner's domain readiness
   score; false means it builds understanding but isn't in the exam blueprint.

``practitioner_profiles.certification_id`` stays nullable at the DB level —
the NOT-NULL enforcement is handled at the API layer (422 validation) so that
existing null rows from earlier phases are not disrupted.

Revision ID: 012
Revises: 011
Create Date: 2026-08-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── certification_domains ──────────────────────────────────────────────────
    op.create_table(
        "certification_domains",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("certification_id", sa.String(36), nullable=False),
        sa.Column("domain_name", sa.Text, nullable=False),
        sa.Column("domain_description", sa.Text, nullable=False),
        # 0–100 integer; all domain rows for one cert must sum to 100
        sa.Column("weight_pct", sa.Numeric(5, 2), nullable=False),
        # Integer from 1 to N — matches official exam guide ordering
        sa.Column("sequence_order", sa.Integer, nullable=False),
        sa.ForeignKeyConstraint(
            ["certification_id"], ["certifications.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_certification_domains_certification_id",
        "certification_domains",
        ["certification_id"],
    )

    # ── certification_domain_scores ────────────────────────────────────────────
    op.create_table(
        "certification_domain_scores",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("practitioner_id", sa.String(36), nullable=False),
        sa.Column("certification_domain_id", sa.String(36), nullable=False),
        sa.Column("mastery_score", sa.Numeric(4, 3), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        # self_assessment_estimate | quiz_derived
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column(
            "last_computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "mastery_score >= 0 AND mastery_score <= 1",
            name="ck_cert_domain_scores_mastery",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_cert_domain_scores_confidence",
        ),
        sa.CheckConstraint(
            "source IN ('self_assessment_estimate','quiz_derived')",
            name="ck_cert_domain_scores_source",
        ),
        sa.ForeignKeyConstraint(
            ["practitioner_id"], ["practitioners.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["certification_domain_id"],
            ["certification_domains.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "practitioner_id",
            "certification_domain_id",
            name="uq_cert_domain_scores_practitioner_domain",
        ),
    )
    op.create_index(
        "ix_cert_domain_scores_practitioner_id",
        "certification_domain_scores",
        ["practitioner_id"],
    )
    op.create_index(
        "ix_cert_domain_scores_domain_id",
        "certification_domain_scores",
        ["certification_domain_id"],
    )

    # ── items: domain-alignment columns ───────────────────────────────────────
    op.add_column(
        "items",
        sa.Column(
            "certification_domain_id",
            sa.String(36),
            sa.ForeignKey("certification_domains.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "items",
        sa.Column(
            "is_cert_evaluated",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index(
        "ix_items_certification_domain_id",
        "items",
        ["certification_domain_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_items_certification_domain_id", table_name="items")
    op.drop_column("items", "is_cert_evaluated")
    op.drop_column("items", "certification_domain_id")

    op.drop_index(
        "ix_cert_domain_scores_domain_id",
        table_name="certification_domain_scores",
    )
    op.drop_index(
        "ix_cert_domain_scores_practitioner_id",
        table_name="certification_domain_scores",
    )
    op.drop_table("certification_domain_scores")

    op.drop_index(
        "ix_certification_domains_certification_id",
        table_name="certification_domains",
    )
    op.drop_table("certification_domains")
