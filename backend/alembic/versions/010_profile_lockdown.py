"""Phase 9.3 — Profile lockdown after first full submission.

Adds ``is_locked`` boolean column to ``practitioner_profiles``.

Once a practitioner saves their skill ratings (the final step of the profile
wizard), the backend atomically sets ``is_locked = true`` on the profile.
A locked profile cannot be edited or re-rated via the API; practitioners can
only view, activate, or delete it. Creating a new profile is the path to
changing direction.

All existing rows are back-filled to ``false`` (unlocked) so they remain
fully editable until the practitioner completes the new wizard flow.

Revision ID: 010
Revises: 009
Create Date: 2026-08-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_locked with a server-side default so the NOT NULL constraint is
    # satisfied immediately for existing rows.
    op.add_column(
        "practitioner_profiles",
        sa.Column(
            "is_locked",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("practitioner_profiles", "is_locked")
