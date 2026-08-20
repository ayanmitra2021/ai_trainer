"""Add is_active column to practitioners

Revision ID: 023
Revises: 022
Create Date: 2026-08-20

Phase 21: admin can deactivate a practitioner account (block login) without
deleting data. is_active = false blocks the /auth/practitioner-login endpoint
with HTTP 403. All data is preserved; the account can be reactivated at any time.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "practitioners",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("practitioners", "is_active")
