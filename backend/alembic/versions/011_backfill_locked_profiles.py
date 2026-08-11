"""Phase 9.3 — Back-fill is_locked for profiles that already have skill assessments.

Migration 010 added ``is_locked`` with ``DEFAULT false``, which correctly leaves
new (unsaved) profiles editable.  However, profiles that were submitted *before*
this column existed — i.e. profiles that already have rows in
``profile_skill_assessments`` — must also be locked so the invariant holds:
"any profile whose skill ratings have been saved is permanently locked."

This migration runs a single UPDATE to lock every such profile:

    UPDATE practitioner_profiles
    SET is_locked = true
    WHERE id IN (SELECT DISTINCT profile_id FROM profile_skill_assessments)

Profiles that have no skill-assessment rows are left unlocked; they are
mid-wizard drafts that the practitioner has not yet finished.

Revision ID: 011
Revises: 010
Create Date: 2026-08-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Lock every profile that already has at least one saved skill-assessment row.
    op.execute(
        sa.text(
            """
            UPDATE practitioner_profiles
            SET    is_locked = true
            WHERE  id IN (
                SELECT DISTINCT profile_id
                FROM   profile_skill_assessments
            )
            """
        )
    )


def downgrade() -> None:
    # Unlock everything — restores the post-010 state where all rows are false.
    op.execute(
        sa.text("UPDATE practitioner_profiles SET is_locked = false")
    )
