"""Phase 13.1 — certification_skills: add domain linkage and source provenance.

Adds two columns to certification_skills:
  - certification_domain_id: nullable FK → certification_domains (ON DELETE SET NULL)
    The exam domain this skill primarily maps to within the cert.
  - source: text NOT NULL server_default='seed'
    Provenance: 'seed' for bootstrap data; 'agent_discovered' for CertSkillMapperAgent rows.

Revision ID: 017
Revises: 016
Create Date: 2026-08-12
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "certification_skills",
        sa.Column(
            "certification_domain_id",
            sa.String(36),
            sa.ForeignKey("certification_domains.id", ondelete="SET NULL", name="fk_cert_skills_domain_id"),
            nullable=True,
        ),
    )
    op.add_column(
        "certification_skills",
        sa.Column(
            "source",
            sa.String(50),
            nullable=False,
            server_default="seed",
        ),
    )


def downgrade() -> None:
    op.drop_column("certification_skills", "source")
    op.drop_constraint("fk_cert_skills_domain_id", "certification_skills", type_="foreignkey")
    op.drop_column("certification_skills", "certification_domain_id")
