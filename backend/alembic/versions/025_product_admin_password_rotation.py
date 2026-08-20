"""Product admin password rotation — Phase 22 follow-up

Revision ID: 025
Revises: 024
Create Date: 2026-08-20

Adds `password_changed_at` to product_admin_users so the 30-day rotation
policy can be enforced on every login.

NULL means the admin has never completed a voluntary password change (i.e.
only the first-login forced change has been done, or the row was seeded
before this migration). The login route treats NULL + must_change_password=False
as "needs rotation" — effectively, the 30-day clock started at account creation.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "product_admin_users",
        sa.Column(
            "password_changed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("product_admin_users", "password_changed_at")
