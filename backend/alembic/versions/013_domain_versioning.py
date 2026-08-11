"""Phase 10.2 — Domain versioning data model: live-refreshable domain versions.

Adds four schema changes plus a backfill:

1. ``certification_domain_versions`` — tracks the history of exam domain snapshots
   for each certification.  A partial unique index on (certification_id) WHERE
   is_current = true enforces exactly one current version per cert.

2. ``certification_domain_proposals`` — pending domain refresh proposals produced
   by the Cert Domain Discovery Agent (Step 10.3), awaiting admin review.

3. ``certification_domains.domain_version_id`` — nullable FK to
   certification_domain_versions.  Set on every existing row by the backfill
   below; new rows always carry this value.

4. ``practitioner_profiles.domain_version_id`` — nullable FK to
   certification_domain_versions.  Null for profiles locked before this step;
   set at profile-lock time from Step 10.5 onward.

Backfill (run inside upgrade):
   For each distinct certification_id already present in certification_domains,
   create one bootstrap certification_domain_versions row
   (version_label = 'bootstrap-step-10.1', is_current = true) and set
   domain_version_id on the matching certification_domains rows.

Revision ID: 013
Revises: 012
Create Date: 2026-08-11
"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Must match the constant in seed/certification_domains.py — do not change one
# without changing the other.
_BOOTSTRAP_VERSION_LABEL = "bootstrap-step-10.1"
_BOOTSTRAP_SOURCE_NOTES = (
    "Bootstrap seed from Phase 10.1 migration data.  "
    "Domain weights verified against official exam guides at Step 10.1 time."
)


def upgrade() -> None:
    # ── certification_domain_versions ─────────────────────────────────────────
    op.create_table(
        "certification_domain_versions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("certification_id", sa.String(36), nullable=False),
        sa.Column("version_label", sa.Text, nullable=False),
        # true = this is the active version for the cert.
        # Partial unique index on (certification_id) WHERE is_current = true
        # enforces that at most one row per cert has is_current = true.
        sa.Column("is_current", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("source_notes", sa.Text, nullable=False),
        # null for bootstrap seed; set for agent-driven refreshes (Step 10.3)
        sa.Column("agent_run_id", sa.String(36), nullable=True),
        # null for bootstrap seed; set for admin-triggered refreshes
        sa.Column("created_by_admin_id", sa.String(36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["certification_id"], ["certifications.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["agent_run_id"], ["agent_runs.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_admin_id"], ["admin_users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cert_domain_versions_certification_id",
        "certification_domain_versions",
        ["certification_id"],
    )
    # Partial unique index: at most one is_current=true row per cert.
    # Postgres-specific; ignored on other dialects.
    op.create_index(
        "uq_cert_domain_versions_current_per_cert",
        "certification_domain_versions",
        ["certification_id"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )

    # ── certification_domain_proposals ────────────────────────────────────────
    op.create_table(
        "certification_domain_proposals",
        sa.Column("id", sa.String(36), nullable=False),
        # null when proposing a brand-new cert not yet in the catalog
        sa.Column("certification_id", sa.String(36), nullable=True),
        # Always set — even if certification_id is null we carry code+name
        sa.Column("cert_code", sa.Text, nullable=False),
        sa.Column("cert_name", sa.Text, nullable=False),
        # JSONB list of {sequence_order, domain_name, domain_description, weight_pct}
        sa.Column("proposed_domains", sa.JSON, nullable=False),
        sa.Column("source_notes", sa.Text, nullable=False),
        sa.Column("agent_run_id", sa.String(36), nullable=False),
        # pending_review | approved | rejected
        sa.Column("status", sa.String(20), nullable=False, server_default="pending_review"),
        sa.Column("reviewed_by_admin_id", sa.String(36), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["certification_id"], ["certifications.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["agent_run_id"], ["agent_runs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_admin_id"], ["admin_users.id"], ondelete="SET NULL"
        ),
        sa.CheckConstraint(
            "status IN ('pending_review','approved','rejected')",
            name="ck_cert_domain_proposals_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cert_domain_proposals_certification_id",
        "certification_domain_proposals",
        ["certification_id"],
    )
    op.create_index(
        "ix_cert_domain_proposals_status",
        "certification_domain_proposals",
        ["status"],
    )

    # ── certification_domains: add domain_version_id ──────────────────────────
    op.add_column(
        "certification_domains",
        sa.Column(
            "domain_version_id",
            sa.String(36),
            sa.ForeignKey(
                "certification_domain_versions.id",
                ondelete="RESTRICT",  # never drop a version that has domains
            ),
            nullable=True,  # null until backfill below; not null from Step 10.3+
        ),
    )
    op.create_index(
        "ix_certification_domains_version_id",
        "certification_domains",
        ["domain_version_id"],
    )

    # ── practitioner_profiles: add domain_version_id ──────────────────────────
    op.add_column(
        "practitioner_profiles",
        sa.Column(
            "domain_version_id",
            sa.String(36),
            sa.ForeignKey(
                "certification_domain_versions.id",
                ondelete="RESTRICT",  # freeze reference at lock time — never cascade
            ),
            nullable=True,  # null for pre-10.2 profiles; set at lock time from 10.5
        ),
    )
    op.create_index(
        "ix_practitioner_profiles_domain_version_id",
        "practitioner_profiles",
        ["domain_version_id"],
    )

    # ── Backfill: bootstrap version rows for every cert that has domain data ───
    #
    # For each distinct certification_id already present in certification_domains,
    # create one bootstrap certification_domain_versions row and link the existing
    # domain rows to it.  If certification_domains is empty (fresh DB), this is a
    # no-op — the seed script creates version rows alongside the domain rows.
    bind = op.get_bind()

    result = bind.execute(
        sa.text("SELECT DISTINCT certification_id FROM certification_domains")
    )
    cert_ids = [row[0] for row in result.fetchall()]

    for cert_id in cert_ids:
        version_id = str(uuid.uuid4())
        bind.execute(
            sa.text(
                "INSERT INTO certification_domain_versions "
                "(id, certification_id, version_label, is_current, source_notes, "
                "agent_run_id, created_by_admin_id, created_at) "
                "VALUES (:id, :cert_id, :label, :is_current, :notes, NULL, NULL, now())"
            ),
            {
                "id": version_id,
                "cert_id": cert_id,
                "label": _BOOTSTRAP_VERSION_LABEL,
                "is_current": True,
                "notes": _BOOTSTRAP_SOURCE_NOTES,
            },
        )
        bind.execute(
            sa.text(
                "UPDATE certification_domains "
                "SET domain_version_id = :version_id "
                "WHERE certification_id = :cert_id AND domain_version_id IS NULL"
            ),
            {"version_id": version_id, "cert_id": cert_id},
        )


def downgrade() -> None:
    op.drop_index(
        "ix_practitioner_profiles_domain_version_id",
        table_name="practitioner_profiles",
    )
    op.drop_column("practitioner_profiles", "domain_version_id")

    op.drop_index(
        "ix_certification_domains_version_id",
        table_name="certification_domains",
    )
    op.drop_column("certification_domains", "domain_version_id")

    op.drop_index(
        "ix_cert_domain_proposals_status",
        table_name="certification_domain_proposals",
    )
    op.drop_index(
        "ix_cert_domain_proposals_certification_id",
        table_name="certification_domain_proposals",
    )
    op.drop_table("certification_domain_proposals")

    op.drop_index(
        "uq_cert_domain_versions_current_per_cert",
        table_name="certification_domain_versions",
    )
    op.drop_index(
        "ix_cert_domain_versions_certification_id",
        table_name="certification_domain_versions",
    )
    op.drop_table("certification_domain_versions")
