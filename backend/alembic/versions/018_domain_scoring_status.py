"""Phase 14.4 — domain_scoring_status on practitioner_profiles.

Adds:
  - practitioner_profiles.domain_scoring_status TEXT NOT NULL DEFAULT 'pending'
  - CHECK constraint for the three valid values
  - Drops and re-adds ck_cert_domain_scores_source to include 'degraded_estimate'

Revision ID: 018
Revises: 017
Create Date: 2026-08-13
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add domain_scoring_status column to practitioner_profiles
    op.add_column(
        "practitioner_profiles",
        sa.Column(
            "domain_scoring_status",
            sa.String(50),
            nullable=False,
            server_default="pending",
        ),
    )
    op.create_check_constraint(
        "ck_domain_scoring_status",
        "practitioner_profiles",
        "domain_scoring_status IN ('pending', 'lm_scored', 'degraded')",
    )

    # 2. Widen the source check constraint on certification_domain_scores to
    #    include 'degraded_estimate'.  SQLAlchemy / Alembic cannot ALTER a CHECK
    #    constraint in-place on Postgres — we must drop and recreate it.
    op.drop_constraint(
        "ck_cert_domain_scores_source",
        "certification_domain_scores",
        type_="check",
    )
    op.create_check_constraint(
        "ck_cert_domain_scores_source",
        "certification_domain_scores",
        "source IN ('self_assessment_estimate','quiz_derived','degraded_estimate')",
    )


def downgrade() -> None:
    # Restore narrow source constraint
    op.drop_constraint(
        "ck_cert_domain_scores_source",
        "certification_domain_scores",
        type_="check",
    )
    op.create_check_constraint(
        "ck_cert_domain_scores_source",
        "certification_domain_scores",
        "source IN ('self_assessment_estimate','quiz_derived')",
    )

    # Remove the new column and its constraint
    op.drop_constraint(
        "ck_domain_scoring_status",
        "practitioner_profiles",
        type_="check",
    )
    op.drop_column("practitioner_profiles", "domain_scoring_status")
