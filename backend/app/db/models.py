"""SQLAlchemy ORM models.

Phase 0 tables: practitioners, skills, skill_profile_events,
skill_profile_snapshots, agent_runs, workflow_runs.

Phase 2 tables: certification_providers, certifications, certification_skills,
practitioner_certification_goals, certification_advisor_responses,
learning_paths, learning_path_items, items, attempts.

Phase 6 tables: practitioner_profiles, profile_skill_assessments.

Phase 7 tables: nudge_categories, mastery_history.
             Altered: nudges (campaign columns).

Phase 9.1: ``rollups`` table dropped — the Rollup model has been removed.
           The RollupReporter agent is archived in agents/_deprecated/.

Phase 10.1 tables: certification_domains, certification_domain_scores.
               Altered: items (certification_domain_id, is_cert_evaluated).

Phase 10.2 tables: certification_domain_versions, certification_domain_proposals.
               Altered: certification_domains (domain_version_id FK),
                        practitioner_profiles (domain_version_id FK).

Phase 10.3: Altered: items (generation column),
                     certification_domain_scores (previous_mastery_score column).

Phase 11 tables: mock_exam_sessions, mock_exam_questions.
             Altered: certifications (exam_question_count, exam_duration_minutes,
                      exam_passing_score_pct).
             Altered: skill_profile_events source constraint (added 'mock_exam').

Phase 13.1: Altered: certification_skills (certification_domain_id, source).

Phase 14.4: Altered: practitioner_profiles (domain_scoring_status).
            Altered: certification_domain_scores source constraint (added 'degraded_estimate').

Phase 22 tables: subscription_plans, organizations, org_enrollment_codes,
                 product_admin_users, org_notification_settings.
             Altered: practitioners (organization_id FK).
             Altered: admin_users (organization_id FK).
             Altered: practitioner_profiles (deleted_at).
             Altered: sessions (product_admin_user_id FK, identity_type constraint).
"""

import uuid
from datetime import UTC, date, datetime

import sqlalchemy as sa
# JSONB and UUID were previously imported here; sa.JSON is used instead for
# cross-database compatibility (SQLite in tests, Postgres in production).
# The migration DDL uses JSONB directly where performance matters.
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> str:
    return str(uuid.uuid4())


def _now_utc() -> datetime:
    """Python-side default for datetime columns.

    Using both server_default (for Postgres DDL) and default (for SQLAlchemy
    INSERT generation) so that SQLite-backed unit tests never hit `now()` which
    only exists in Postgres.
    """
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Shared declarative base for all models."""


# ── practitioners ─────────────────────────────────────────────────────────────

class Practitioner(Base):
    """Who the system is about — one row per person."""

    __tablename__ = "practitioners"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=_uuid
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    email: Mapped[str] = mapped_column(sa.String(255), nullable=False, unique=True, index=True)
    role: Mapped[str | None] = mapped_column(sa.String(255))
    practice: Mapped[str | None] = mapped_column(sa.String(255))
    seniority_level: Mapped[str | None] = mapped_column(sa.String(100))
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true"), default=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        default=_now_utc,
        nullable=False,
    )
    # Phase 22: org membership — nullable FK to organizations
    organization_id: Mapped[str | None] = mapped_column(
        sa.String(36),
        sa.ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    organization: Mapped["Organization | None"] = relationship(
        back_populates="practitioners",
        foreign_keys="[Practitioner.organization_id]",
    )

    # Relationships (back-populated as later phases add tables)
    skill_profile_events: Mapped[list["SkillProfileEvent"]] = relationship(
        back_populates="practitioner", cascade="all, delete-orphan"
    )
    skill_profile_snapshots: Mapped[list["SkillProfileSnapshot"]] = relationship(
        back_populates="practitioner", cascade="all, delete-orphan"
    )
    certification_goals: Mapped[list["PractitionerCertificationGoal"]] = relationship(
        back_populates="practitioner", cascade="all, delete-orphan"
    )
    certification_advisor_responses: Mapped[list["CertificationAdvisorResponse"]] = relationship(
        back_populates="practitioner", cascade="all, delete-orphan"
    )
    learning_paths: Mapped[list["LearningPath"]] = relationship(
        back_populates="practitioner", cascade="all, delete-orphan"
    )
    attempts: Mapped[list["Attempt"]] = relationship(
        back_populates="practitioner", cascade="all, delete-orphan"
    )
    usage_events: Mapped[list["UsageEvent"]] = relationship(
        back_populates="practitioner", cascade="all, delete-orphan"
    )
    correlation_snapshots: Mapped[list["CorrelationSnapshot"]] = relationship(
        back_populates="practitioner", cascade="all, delete-orphan"
    )
    nudges: Mapped[list["Nudge"]] = relationship(
        back_populates="practitioner", cascade="all, delete-orphan"
    )
    profiles: Mapped[list["PractitionerProfile"]] = relationship(
        back_populates="practitioner", cascade="all, delete-orphan"
    )
    mastery_history: Mapped[list["MasteryHistory"]] = relationship(
        back_populates="practitioner", cascade="all, delete-orphan"
    )
    certification_domain_scores: Mapped[list["CertificationDomainScore"]] = relationship(
        back_populates="practitioner", cascade="all, delete-orphan"
    )
    mock_exam_sessions: Mapped[list["MockExamSession"]] = relationship(
        back_populates="practitioner", cascade="all, delete-orphan"
    )
    byte_sized_lessons: Mapped[list["ByteSizedLesson"]] = relationship(
        back_populates="practitioner", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Practitioner id={self.id!r} email={self.email!r}>"


# ── skills ────────────────────────────────────────────────────────────────────

class Skill(Base):
    """Skill graph node — shared between Mastery Mesh and Adoption Pulse."""

    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=_uuid
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False, index=True)
    category: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    # Nullable self-FK for hierarchical skill graph
    parent_skill_id: Mapped[str | None] = mapped_column(
        sa.String(36), sa.ForeignKey("skills.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str | None] = mapped_column(sa.Text)

    children: Mapped[list["Skill"]] = relationship(
        "Skill",
        backref=sa.orm.backref("parent", remote_side="Skill.id"),
    )
    skill_profile_events: Mapped[list["SkillProfileEvent"]] = relationship(
        back_populates="skill"
    )
    skill_profile_snapshots: Mapped[list["SkillProfileSnapshot"]] = relationship(
        back_populates="skill"
    )
    usage_events: Mapped[list["UsageEvent"]] = relationship(back_populates="skill")
    correlation_snapshots: Mapped[list["CorrelationSnapshot"]] = relationship(
        back_populates="skill"
    )
    mastery_history: Mapped[list["MasteryHistory"]] = relationship(
        back_populates="skill", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Skill id={self.id!r} name={self.name!r}>"


# ── skill_profile_events (append-only) ────────────────────────────────────────

class SkillProfileEvent(Base):
    """Raw evidence of what a practitioner knows, from any source.

    Append-only — never updated or deleted. The Skill Profiler Agent reads these
    to compute (or recompute) skill_profile_snapshots.
    """

    __tablename__ = "skill_profile_events"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=_uuid
    )
    practitioner_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("practitioners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # One of: certification | self_assessment | quiz_attempt | project_history
    source: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    # 0–1 float representing signal strength
    signal_strength: Mapped[float] = mapped_column(sa.Numeric(4, 3), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    # Extra context: which cert, which attempt id, etc.
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", sa.JSON, nullable=True
    )

    practitioner: Mapped["Practitioner"] = relationship(
        back_populates="skill_profile_events"
    )
    skill: Mapped["Skill"] = relationship(back_populates="skill_profile_events")

    __table_args__ = (
        sa.CheckConstraint(
            "source IN ('certification','self_assessment','quiz_attempt','project_history','mock_exam')",
            name="ck_skill_profile_events_source",
        ),
        sa.CheckConstraint(
            "signal_strength >= 0 AND signal_strength <= 1",
            name="ck_skill_profile_events_signal_strength",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<SkillProfileEvent id={self.id!r} source={self.source!r} "
            f"practitioner={self.practitioner_id!r}>"
        )


# ── skill_profile_snapshots (derived) ─────────────────────────────────────────

class SkillProfileSnapshot(Base):
    """Current best estimate per practitioner × skill.

    Rebuilt by the Skill Profiler Agent; never hand-edited. The composite PK
    means there is at most one snapshot per (practitioner, skill) pair — the
    Agent upserts rather than appending.
    """

    __tablename__ = "skill_profile_snapshots"

    practitioner_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("practitioners.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
    )
    skill_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
    )
    mastery_score: Mapped[float] = mapped_column(
        sa.Numeric(4, 3), nullable=False, comment="0–1 mastery estimate"
    )
    confidence: Mapped[float] = mapped_column(
        sa.Numeric(4, 3), nullable=False, comment="0–1 confidence in the estimate"
    )
    last_computed_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )

    practitioner: Mapped["Practitioner"] = relationship(
        back_populates="skill_profile_snapshots"
    )
    skill: Mapped["Skill"] = relationship(back_populates="skill_profile_snapshots")

    __table_args__ = (
        sa.CheckConstraint(
            "mastery_score >= 0 AND mastery_score <= 1",
            name="ck_skill_profile_snapshots_mastery",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_skill_profile_snapshots_confidence",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<SkillProfileSnapshot practitioner={self.practitioner_id!r} "
            f"skill={self.skill_id!r} mastery={self.mastery_score}>"
        )


# ── workflow_runs ──────────────────────────────────────────────────────────────

class WorkflowRun(Base):
    """One row per workflow execution. Agent runs link back to it."""

    __tablename__ = "workflow_runs"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=_uuid
    )
    # One of: recommend_certification | generate_learning_path | nightly_pulse
    workflow_name: Mapped[str] = mapped_column(sa.String(100), nullable=False, index=True)
    triggered_by: Mapped[str | None] = mapped_column(
        sa.String(255), comment="practitioner_id, schedule, or admin"
    )
    # One of: running | completed | failed
    status: Mapped[str] = mapped_column(
        sa.String(20), nullable=False, default="running"
    )
    started_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )

    agent_runs: Mapped[list["AgentRun"]] = relationship(
        back_populates="workflow_run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        sa.CheckConstraint(
            "status IN ('running','completed','failed','partial')",
            name="ck_workflow_runs_status",
        ),
    )

    def __repr__(self) -> str:
        return f"<WorkflowRun id={self.id!r} name={self.workflow_name!r} status={self.status!r}>"


# ── agent_runs ────────────────────────────────────────────────────────────────

class AgentRun(Base):
    """Every agent invocation — the observability and cost-tracking backbone.

    Written by Agent.run() in base.py; never written directly by callers.
    """

    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=_uuid
    )
    agent_name: Mapped[str] = mapped_column(sa.String(100), nullable=False, index=True)
    workflow_run_id: Mapped[str | None] = mapped_column(
        sa.String(36),
        sa.ForeignKey("workflow_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Serialized input/output — stored as JSON (JSONB on Postgres)
    input: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    output: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    model_used: Mapped[str | None] = mapped_column(sa.String(100))
    tokens_input: Mapped[int | None] = mapped_column(sa.Integer)
    tokens_output: Mapped[int | None] = mapped_column(sa.Integer)
    latency_ms: Mapped[int | None] = mapped_column(sa.Integer)
    # One of: success | error
    status: Mapped[str] = mapped_column(sa.String(20), nullable=False, default="success")
    error_message: Mapped[str | None] = mapped_column(sa.Text)
    started_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )

    workflow_run: Mapped["WorkflowRun | None"] = relationship(back_populates="agent_runs")

    __table_args__ = (
        sa.CheckConstraint(
            "status IN ('success','error')",
            name="ck_agent_runs_status",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<AgentRun id={self.id!r} agent={self.agent_name!r} status={self.status!r}>"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 2 — Mastery Mesh tables
# ═══════════════════════════════════════════════════════════════════════════════


# ── certification_providers ───────────────────────────────────────────────────

class CertificationProvider(Base):
    """Any certifying body — Anthropic, AWS, Google Cloud, Microsoft, etc."""

    __tablename__ = "certification_providers"

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False, unique=True, index=True)
    website: Mapped[str | None] = mapped_column(sa.String(500))
    notes: Mapped[str | None] = mapped_column(sa.Text)

    certifications: Mapped[list["Certification"]] = relationship(
        back_populates="provider", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<CertificationProvider id={self.id!r} name={self.name!r}>"


# ── certifications ────────────────────────────────────────────────────────────

class Certification(Base):
    """One row per credential — provider-agnostic."""

    __tablename__ = "certifications"

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    provider_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("certification_providers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(sa.String(100), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    # foundational | associate | professional | specialty | expert
    level: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    requires_coding_background: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=False
    )
    typical_audience: Mapped[str | None] = mapped_column(sa.Text)
    focus_area: Mapped[str | None] = mapped_column(sa.Text)
    exam_format: Mapped[str | None] = mapped_column(sa.Text)
    eligibility_notes: Mapped[str | None] = mapped_column(sa.Text)
    external_url: Mapped[str | None] = mapped_column(sa.String(500))
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    last_verified_at: Mapped[date | None] = mapped_column(sa.Date)

    # Phase 11: exam configuration — nullable (not all certs have structured exams)
    exam_question_count: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    exam_duration_minutes: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    # e.g. 70.00 for 70%
    exam_passing_score_pct: Mapped[float | None] = mapped_column(
        sa.Numeric(5, 2), nullable=True
    )

    provider: Mapped["CertificationProvider"] = relationship(back_populates="certifications")
    certification_skills: Mapped[list["CertificationSkill"]] = relationship(
        back_populates="certification", cascade="all, delete-orphan"
    )
    practitioner_goals: Mapped[list["PractitionerCertificationGoal"]] = relationship(
        back_populates="certification", cascade="all, delete-orphan"
    )
    domains: Mapped[list["CertificationDomain"]] = relationship(
        back_populates="certification",
        cascade="all, delete-orphan",
        order_by="CertificationDomain.sequence_order",
    )
    # Phase 10.2: version history for this cert's exam domain definitions
    domain_versions: Mapped[list["CertificationDomainVersion"]] = relationship(
        back_populates="certification", cascade="all, delete-orphan"
    )
    # Phase 10.2: domain refresh proposals produced by the Cert Domain Discovery Agent
    domain_proposals: Mapped[list["CertificationDomainProposal"]] = relationship(
        back_populates="certification", cascade="all, delete-orphan"
    )
    # Phase 11: mock exam sessions for this certification
    mock_exam_sessions: Mapped[list["MockExamSession"]] = relationship(
        back_populates="certification", cascade="all, delete-orphan"
    )

    __table_args__ = (
        sa.CheckConstraint(
            "level IN ('foundational','associate','professional','specialty','expert')",
            name="ck_certifications_level",
        ),
    )

    def __repr__(self) -> str:
        return f"<Certification code={self.code!r} name={self.name!r}>"


# ── certification_skills ──────────────────────────────────────────────────────

class CertificationSkill(Base):
    """Maps a certification to the skill graph nodes it covers, with a weight."""

    __tablename__ = "certification_skills"

    certification_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("certifications.id", ondelete="CASCADE"),
        primary_key=True,
    )
    skill_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("skills.id", ondelete="CASCADE"),
        primary_key=True,
    )
    # 0–1 float: how central this skill is to the certification's exam
    weight: Mapped[float] = mapped_column(sa.Numeric(4, 3), nullable=False, default=1.0)

    # Phase 13.1: exam domain this skill primarily belongs to in the cert.
    # Null for seed rows written before Phase 13; always set for agent_discovered rows.
    certification_domain_id: Mapped[str | None] = mapped_column(
        sa.String(36),
        sa.ForeignKey("certification_domains.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Phase 13.1: provenance — 'seed' for bootstrap data; 'agent_discovered' for mapper rows.
    source: Mapped[str] = mapped_column(
        sa.String(50), nullable=False, server_default="seed", default="seed"
    )

    certification: Mapped["Certification"] = relationship(back_populates="certification_skills")
    skill: Mapped["Skill"] = relationship()
    certification_domain: Mapped["CertificationDomain | None"] = relationship(
        foreign_keys=[certification_domain_id],
    )

    __table_args__ = (
        sa.CheckConstraint(
            "weight >= 0 AND weight <= 1",
            name="ck_certification_skills_weight",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<CertificationSkill cert={self.certification_id!r} "
            f"skill={self.skill_id!r} weight={self.weight}>"
        )


# ── certification_domains ─────────────────────────────────────────────────────

class CertificationDomain(Base):
    """Official exam domain/module for a certification — Phase 10.1.

    One row per domain section in the official exam guide.  The ``weight_pct``
    values for all domains of a given certification must sum to 100 (allow ±1
    for rounding differences between providers).

    ``sequence_order`` matches the official exam guide numbering (Domain 1,
    Domain 2, …) and is used for display ordering in the gap chart.

    Phase 10.2: every row belongs to a ``CertificationDomainVersion``.  The
    ``domain_version_id`` FK is nullable for rows that pre-date the 013
    migration but is always set on rows written after that migration.  Rows are
    never deleted once a profile references them via ``domain_version_id`` —
    the FK ondelete=RESTRICT enforces this.
    """

    __tablename__ = "certification_domains"

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    certification_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("certifications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Phase 10.2: which version snapshot this row belongs to.
    # Nullable for rows that pre-date the 013 migration; always set for new rows.
    domain_version_id: Mapped[str | None] = mapped_column(
        sa.String(36),
        sa.ForeignKey("certification_domain_versions.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    domain_name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    domain_description: Mapped[str] = mapped_column(sa.Text, nullable=False)
    # Percentage of the exam (0–100).  All rows for one cert must sum to 100.
    weight_pct: Mapped[float] = mapped_column(sa.Numeric(5, 2), nullable=False)
    # 1-based ordering from the official exam guide
    sequence_order: Mapped[int] = mapped_column(sa.Integer, nullable=False)

    certification: Mapped["Certification"] = relationship(
        back_populates="domains"
    )
    version: Mapped["CertificationDomainVersion | None"] = relationship(
        back_populates="domains"
    )
    domain_scores: Mapped[list["CertificationDomainScore"]] = relationship(
        back_populates="domain", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<CertificationDomain cert={self.certification_id!r} "
            f"name={self.domain_name!r} weight={self.weight_pct}%>"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 10.2 — Domain versioning tables
# ═══════════════════════════════════════════════════════════════════════════════


# ── certification_domain_versions ─────────────────────────────────────────────

class CertificationDomainVersion(Base):
    """Snapshot of a certification's exam domain definitions — Phase 10.2.

    Each set of official domain definitions for a certification is one version
    row.  The bootstrap seed (Step 10.1) creates version 1; admin-triggered
    refreshes via the Cert Domain Discovery Agent (Step 10.3) create new
    versions.

    Partial unique index on (certification_id) WHERE is_current = true enforces
    that at most one version per cert is the "live" version at any time.  On
    Postgres (production + integration tests) this is a real partial index.
    On SQLite (unit tests) the WHERE clause is silently dropped — unit tests do
    not exercise multi-version scenarios so this is acceptable.

    **Freeze semantics:** ``practitioner_profiles.domain_version_id`` is set at
    profile-lock time (Step 10.5) to the then-current version.  A subsequent
    admin refresh creates a new version; the practitioner's pinned version and
    their domain scores are never retroactively changed.
    """

    __tablename__ = "certification_domain_versions"

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    certification_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("certifications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Human-readable label — e.g. "bootstrap-step-10.1" or "2025-Q1-refresh"
    version_label: Mapped[str] = mapped_column(sa.Text, nullable=False)
    # True = this is the active version for the cert (partial unique index enforces one per cert)
    is_current: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=True, server_default=sa.text("true")
    )
    # Where the data came from: exam guide URL, agent confidence notes, or "bootstrap seed"
    source_notes: Mapped[str] = mapped_column(sa.Text, nullable=False, default="")
    # null for bootstrap seed; set when an agent-driven refresh produced this version
    agent_run_id: Mapped[str | None] = mapped_column(
        sa.String(36),
        sa.ForeignKey("agent_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    # null for bootstrap seed; set for admin-triggered refreshes
    created_by_admin_id: Mapped[str | None] = mapped_column(
        sa.String(36),
        sa.ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        default=_now_utc,
        nullable=False,
    )

    certification: Mapped["Certification"] = relationship(
        back_populates="domain_versions"
    )
    domains: Mapped[list["CertificationDomain"]] = relationship(
        back_populates="version"
    )
    # Profiles that were locked against this version
    locked_profiles: Mapped[list["PractitionerProfile"]] = relationship(
        back_populates="domain_version",
        foreign_keys="PractitionerProfile.domain_version_id",
    )

    __table_args__ = (
        # Partial unique index: at most one row per cert may have is_current=True.
        # On Postgres this creates a proper partial index; on SQLite the WHERE
        # clause is dropped (creating a regular unique index on certification_id,
        # which is acceptable since unit tests don't create multiple versions).
        sa.Index(
            "uq_cert_domain_versions_current_per_cert",
            "certification_id",
            unique=True,
            postgresql_where=sa.text("is_current = true"),
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<CertificationDomainVersion id={self.id!r} "
            f"cert={self.certification_id!r} label={self.version_label!r} "
            f"current={self.is_current}>"
        )


# ── certification_domain_proposals ────────────────────────────────────────────

class CertificationDomainProposal(Base):
    """Pending domain refresh proposal from the Cert Domain Discovery Agent — Phase 10.2/10.3.

    Each row represents one agent run's output for one certification, awaiting
    admin review.  Approved proposals become new ``CertificationDomainVersion``
    rows plus fresh ``CertificationDomain`` rows; rejected proposals are
    archived with a rejection reason.

    When ``certification_id`` is null the agent is proposing a brand-new
    certification not yet in the catalog.  Approving such a proposal creates a
    ``Certification`` row with ``is_active = false`` for separate admin
    activation.
    """

    __tablename__ = "certification_domain_proposals"

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    # null when proposing a brand-new cert not yet in certifications
    certification_id: Mapped[str | None] = mapped_column(
        sa.String(36),
        sa.ForeignKey("certifications.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Always set — even when certification_id is null
    cert_code: Mapped[str] = mapped_column(sa.Text, nullable=False)
    cert_name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    # JSONB: list of {sequence_order, domain_name, domain_description, weight_pct}
    proposed_domains: Mapped[list] = mapped_column(sa.JSON, nullable=False, default=list)
    # Agent's explanation of where data was found and confidence level
    source_notes: Mapped[str] = mapped_column(sa.Text, nullable=False, default="")
    # The agent_runs row that produced this proposal
    agent_run_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    # pending_review | approved | rejected
    status: Mapped[str] = mapped_column(
        sa.String(20), nullable=False, default="pending_review"
    )
    reviewed_by_admin_id: Mapped[str | None] = mapped_column(
        sa.String(36),
        sa.ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    rejection_notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        default=_now_utc,
        nullable=False,
    )

    certification: Mapped["Certification | None"] = relationship(
        back_populates="domain_proposals"
    )

    __table_args__ = (
        sa.CheckConstraint(
            "status IN ('pending_review','approved','rejected')",
            name="ck_cert_domain_proposals_status",
        ),
        sa.Index("ix_cert_domain_proposals_status", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<CertificationDomainProposal id={self.id!r} "
            f"cert_code={self.cert_code!r} status={self.status!r}>"
        )


# ── practitioner_certification_goals ──────────────────────────────────────────

class PractitionerCertificationGoal(Base):
    """A practitioner's relationship with one certification over time."""

    __tablename__ = "practitioner_certification_goals"

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    practitioner_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("practitioners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    certification_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("certifications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # recommended | selected | in_progress | achieved | abandoned
    status: Mapped[str] = mapped_column(sa.String(30), nullable=False, default="recommended")
    recommended_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False,
        server_default=sa.text("now()"), default=_now_utc,
    )
    selected_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    achieved_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    profile_id: Mapped[str | None] = mapped_column(
        sa.String(36),
        sa.ForeignKey("practitioner_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )

    practitioner: Mapped["Practitioner"] = relationship(back_populates="certification_goals")
    certification: Mapped["Certification"] = relationship(back_populates="practitioner_goals")

    __table_args__ = (
        sa.CheckConstraint(
            "status IN ('recommended','selected','in_progress','achieved','abandoned')",
            name="ck_practitioner_cert_goals_status",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<PractitionerCertificationGoal practitioner={self.practitioner_id!r} "
            f"cert={self.certification_id!r} status={self.status!r}>"
        )


# ── certification_advisor_responses ───────────────────────────────────────────

class CertificationAdvisorResponse(Base):
    """Raw questionnaire answers — kept for auditing and prompt iteration."""

    __tablename__ = "certification_advisor_responses"

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    practitioner_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("practitioners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Full questionnaire answers as submitted — stored verbatim for auditability
    responses: Mapped[dict] = mapped_column(sa.JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False,
        server_default=sa.text("now()"), default=_now_utc,
    )
    profile_id: Mapped[str | None] = mapped_column(
        sa.String(36),
        sa.ForeignKey("practitioner_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )

    practitioner: Mapped["Practitioner"] = relationship(
        back_populates="certification_advisor_responses"
    )

    def __repr__(self) -> str:
        return (
            f"<CertificationAdvisorResponse id={self.id!r} "
            f"practitioner={self.practitioner_id!r}>"
        )


# ── learning_paths / learning_path_items ──────────────────────────────────────

class LearningPath(Base):
    """The Curriculum Planner's output — one per run, not updated in place."""

    __tablename__ = "learning_paths"

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    practitioner_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("practitioners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    generated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False,
        server_default=sa.text("now()"), default=_now_utc,
    )
    # draft | active | completed
    status: Mapped[str] = mapped_column(sa.String(20), nullable=False, default="draft")
    workflow_run_id: Mapped[str | None] = mapped_column(
        sa.String(36),
        sa.ForeignKey("workflow_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    practitioner: Mapped["Practitioner"] = relationship(back_populates="learning_paths")
    items: Mapped[list["LearningPathItem"]] = relationship(
        back_populates="learning_path", cascade="all, delete-orphan",
        order_by="LearningPathItem.sequence_order",
    )

    __table_args__ = (
        sa.CheckConstraint(
            "status IN ('draft','active','completed')",
            name="ck_learning_paths_status",
        ),
    )

    def __repr__(self) -> str:
        return f"<LearningPath id={self.id!r} practitioner={self.practitioner_id!r}>"


class LearningPathItem(Base):
    """One node in a practitioner's learning path."""

    __tablename__ = "learning_path_items"

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    learning_path_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("learning_paths.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence_order: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    # item_set | scenario_lab | external_reading
    resource_type: Mapped[str] = mapped_column(sa.String(50), nullable=False, default="item_set")
    # pending | in_progress | done
    status: Mapped[str] = mapped_column(sa.String(20), nullable=False, default="pending")
    rationale: Mapped[str | None] = mapped_column(sa.Text)
    # Phase 17.5: quiz generation state — pending | ready | failed
    quiz_status: Mapped[str] = mapped_column(sa.String(20), nullable=False, default="pending")

    learning_path: Mapped["LearningPath"] = relationship(back_populates="items")
    skill: Mapped["Skill"] = relationship()

    __table_args__ = (
        sa.CheckConstraint(
            "resource_type IN ('item_set','scenario_lab','external_reading')",
            name="ck_learning_path_items_resource_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending','in_progress','done')",
            name="ck_learning_path_items_status",
        ),
        sa.CheckConstraint(
            "quiz_status IN ('pending','ready','failed')",
            name="ck_learning_path_items_quiz_status",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<LearningPathItem id={self.id!r} order={self.sequence_order} "
            f"skill={self.skill_id!r}>"
        )


# ── items ─────────────────────────────────────────────────────────────────────

class Item(Base):
    """Practice item (MCQ / free-text / scenario) from the Item-Writer Agent."""

    __tablename__ = "items"

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    skill_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # mcq | free_text | scenario
    item_type: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    prompt: Mapped[str] = mapped_column(sa.Text, nullable=False)
    # MCQ: {options: [...], correct_index: int, trap_index: int | null}
    # free_text: {model_answer: str, key_points: [...]}
    answer_key: Mapped[dict] = mapped_column(sa.JSON, nullable=False)
    # The reveal copy for the trap mechanic — null for non-MCQ or items with no trap
    trap_explanation: Mapped[str | None] = mapped_column(sa.Text)
    difficulty: Mapped[float] = mapped_column(
        sa.Numeric(4, 3), nullable=False, default=0.5
    )
    # Running calibration data: {attempt_count, avg_score, trap_selection_rate}
    calibration_stats: Mapped[dict | None] = mapped_column(sa.JSON)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False,
        server_default=sa.text("now()"), default=_now_utc,
    )
    # Phase 10.1: domain alignment — NULL on legacy items (pre-10.3); set on all
    # items generated after Step 10.3.
    certification_domain_id: Mapped[str | None] = mapped_column(
        sa.String(36),
        sa.ForeignKey("certification_domains.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # True when the topic is directly assessed in the cert exam blueprint;
    # False for supplementary items that build understanding only.
    is_cert_evaluated: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=False
    )
    # Phase 10.3: which refresh round this item belongs to (1-indexed).
    # Mastery ceiling formula: ceiling(N) = 1 - 0.5^N where N = rounds_completed.
    generation: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=1
    )

    skill: Mapped["Skill"] = relationship()
    attempts: Mapped[list["Attempt"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )
    certification_domain: Mapped["CertificationDomain | None"] = relationship(
        foreign_keys=[certification_domain_id]
    )

    __table_args__ = (
        sa.CheckConstraint(
            "item_type IN ('mcq','free_text','scenario')",
            name="ck_items_item_type",
        ),
        sa.CheckConstraint(
            "difficulty >= 0 AND difficulty <= 1",
            name="ck_items_difficulty",
        ),
    )

    def __repr__(self) -> str:
        return f"<Item id={self.id!r} type={self.item_type!r} skill={self.skill_id!r}>"


# ── attempts ──────────────────────────────────────────────────────────────────

class Attempt(Base):
    """A practitioner's scored response to an item — written by the Grader Agent."""

    __tablename__ = "attempts"

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    practitioner_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("practitioners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Submitted response: {selected_index: int} for MCQ, {text: str} for free_text
    response: Mapped[dict] = mapped_column(sa.JSON, nullable=False)
    score: Mapped[float] = mapped_column(sa.Numeric(4, 3), nullable=False)
    grader_rationale: Mapped[str] = mapped_column(sa.Text, nullable=False)
    # True if the practitioner selected the trap option; null for non-MCQ items
    is_trap_selected: Mapped[bool | None] = mapped_column(sa.Boolean)
    attempted_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False,
        server_default=sa.text("now()"), default=_now_utc,
    )

    practitioner: Mapped["Practitioner"] = relationship(back_populates="attempts")
    item: Mapped["Item"] = relationship(back_populates="attempts")

    __table_args__ = (
        sa.CheckConstraint(
            "score >= 0 AND score <= 1",
            name="ck_attempts_score",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Attempt id={self.id!r} practitioner={self.practitioner_id!r} "
            f"score={self.score}>"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 3 — Adoption Pulse tables
# ═══════════════════════════════════════════════════════════════════════════════


# ── usage_events (append-only) ────────────────────────────────────────────────

class UsageEvent(Base):
    """Adoption Pulse raw signal — normalized and append-only.

    Written by the Usage-Signal Agent; never updated in place. The Correlation
    Agent reads these alongside skill_profile_snapshots to compute gap scores.
    """

    __tablename__ = "usage_events"

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    practitioner_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("practitioners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # claude_code_session | git_commit | other
    signal_type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    # Nullable — inferred from MCP mapping; null means ambiguous / unmapped
    skill_id: Mapped[str | None] = mapped_column(
        sa.String(36),
        sa.ForeignKey("skills.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Pointer back to source record — we store the ref, not the raw payload
    raw_ref: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, index=True
    )
    ingested_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False,
        server_default=sa.text("now()"), default=_now_utc,
    )

    practitioner: Mapped["Practitioner"] = relationship(back_populates="usage_events")
    skill: Mapped["Skill | None"] = relationship(back_populates="usage_events")

    __table_args__ = (
        sa.CheckConstraint(
            "signal_type IN ('claude_code_session','git_commit','other')",
            name="ck_usage_events_signal_type",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<UsageEvent id={self.id!r} type={self.signal_type!r} "
            f"skill={self.skill_id!r}>"
        )


# ── correlation_snapshots (derived, append-only history) ──────────────────────

class CorrelationSnapshot(Base):
    """Correlation Agent output: trained vs. adopted, per practitioner × skill.

    Unlike skill_profile_snapshots (which has a composite PK — one row per
    practitioner × skill), correlation_snapshots keep history: each nightly run
    appends new rows rather than upsert. This lets the Trend Dashboard (Phase 4)
    show how gaps evolve over time.
    """

    __tablename__ = "correlation_snapshots"

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    practitioner_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("practitioners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Score from skill_profile_snapshots at computation time
    trained_score: Mapped[float] = mapped_column(sa.Numeric(4, 3), nullable=False)
    # 0–1 estimate derived from usage_events recency/density
    adoption_score: Mapped[float] = mapped_column(sa.Numeric(4, 3), nullable=False)
    # Meaningful only when trained_score >= 0.5; low mastery is a training need, not a gap
    gap_score: Mapped[float] = mapped_column(sa.Numeric(4, 3), nullable=False)
    has_adoption_gap: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    # Agent's reasoning — human-readable, kept for debugging and review
    reasoning: Mapped[str | None] = mapped_column(sa.Text)
    computed_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False,
        server_default=sa.text("now()"), default=_now_utc,
    )

    practitioner: Mapped["Practitioner"] = relationship(back_populates="correlation_snapshots")
    skill: Mapped["Skill"] = relationship(back_populates="correlation_snapshots")

    __table_args__ = (
        sa.CheckConstraint(
            "trained_score >= 0 AND trained_score <= 1",
            name="ck_correlation_trained_score",
        ),
        sa.CheckConstraint(
            "adoption_score >= 0 AND adoption_score <= 1",
            name="ck_correlation_adoption_score",
        ),
        sa.CheckConstraint(
            "gap_score >= 0 AND gap_score <= 1",
            name="ck_correlation_gap_score",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<CorrelationSnapshot practitioner={self.practitioner_id!r} "
            f"skill={self.skill_id!r} gap={self.gap_score} at={self.computed_at}>"
        )


# ── nudges ────────────────────────────────────────────────────────────────────

class Nudge(Base):
    """Individual nudge drafted by the Nudge Composer Agent.

    Nothing auto-sends. Status starts at 'drafted'; a human approves to 'approved'
    before any delivery mechanism marks it 'sent'. See docs/human-in-the-loop.md.
    """

    __tablename__ = "nudges"

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    practitioner_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("practitioners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # gap_alert | encouragement | reminder
    nudge_type: Mapped[str] = mapped_column(sa.String(30), nullable=False)
    # email | in_app
    channel: Mapped[str] = mapped_column(sa.String(30), nullable=False, default="in_app")
    # The actual message text — drafted by the agent; reviewed before approval
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    # drafted → approved → sent
    status: Mapped[str] = mapped_column(sa.String(20), nullable=False, default="drafted")
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False,
        server_default=sa.text("now()"), default=_now_utc,
    )
    sent_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    # Agent reasoning — kept for human review before approval
    composer_reasoning: Mapped[str | None] = mapped_column(sa.Text)

    # Phase 7 campaign columns
    nudge_category_id: Mapped[str | None] = mapped_column(
        sa.String(36),
        sa.ForeignKey("nudge_categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    subject: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    read_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    created_by_admin_id: Mapped[str | None] = mapped_column(
        sa.String(36),
        sa.ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    practitioner: Mapped["Practitioner"] = relationship(back_populates="nudges")
    nudge_category: Mapped["NudgeCategory | None"] = relationship(back_populates="nudges")

    __table_args__ = (
        sa.CheckConstraint(
            "nudge_type IN ('gap_alert','encouragement','reminder','campaign')",
            name="ck_nudges_type",
        ),
        sa.CheckConstraint(
            "channel IN ('email','in_app')",
            name="ck_nudges_channel",
        ),
        sa.CheckConstraint(
            "status IN ('drafted','approved','sent')",
            name="ck_nudges_status",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Nudge id={self.id!r} practitioner={self.practitioner_id!r} "
            f"type={self.nudge_type!r} status={self.status!r}>"
        )


# ── rollups ───────────────────────────────────────────────────────────────────
# Phase 9.1: The Rollup ORM model has been removed.
# The ``rollups`` table is dropped by migration 009_remove_rollups.py.
# The archived model definition is in agents/_deprecated/rollup_reporter.py.


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 7 — Smart Nudge tables
# ═══════════════════════════════════════════════════════════════════════════════


# ── nudge_categories ─────────────────────────────────────────────────────────

class NudgeCategory(Base):
    """Admin-driven nudge category — generated by LLM from aggregate KPIs or typed manually."""

    __tablename__ = "nudge_categories"

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    title: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    description: Mapped[str] = mapped_column(sa.Text, nullable=False)
    # Use sa.JSON for cross-database compatibility (JSONB used in the migration DDL)
    criteria: Mapped[dict] = mapped_column(sa.JSON, nullable=False)
    is_custom: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    tone_hint: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    estimated_reach: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    created_by_admin_id: Mapped[str | None] = mapped_column(
        sa.String(36),
        sa.ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        default=_now_utc,
        nullable=False,
    )

    nudges: Mapped[list["Nudge"]] = relationship(back_populates="nudge_category")

    def __repr__(self) -> str:
        return f"<NudgeCategory id={self.id!r} title={self.title!r}>"


# ── mastery_history ───────────────────────────────────────────────────────────

class MasteryHistory(Base):
    """Append-only mastery score history for trend charts (Phase 7.5).

    A row is appended every time the Skill Profiler upserts skill_profile_snapshots.
    Retain only 90 days of history per practitioner (enforced in the profiler workflow).
    """

    __tablename__ = "mastery_history"

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    practitioner_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("practitioners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mastery_score: Mapped[float] = mapped_column(sa.Numeric(4, 3), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        default=_now_utc,
        nullable=False,
        index=True,
    )

    practitioner: Mapped["Practitioner"] = relationship(back_populates="mastery_history")
    skill: Mapped["Skill"] = relationship(back_populates="mastery_history")

    def __repr__(self) -> str:
        return (
            f"<MasteryHistory practitioner={self.practitioner_id!r} "
            f"skill={self.skill_id!r} score={self.mastery_score} at={self.recorded_at}>"
        )


# ── certification_domain_scores (derived) ─────────────────────────────────────

class CertificationDomainScore(Base):
    """Per-practitioner, per-domain mastery score — Phase 10.1.

    Three source values:
    - ``self_assessment_estimate`` — written by the Domain Scorer Agent at
      profile-lock time (Step 10.2).  Max confidence capped at 0.5.
    - ``quiz_derived`` — written when the practitioner submits cert-evaluated
      quiz answers for this domain (Step 10.4).  Takes precedence and is never
      overwritten by a ``self_assessment_estimate``.
    - ``degraded_estimate`` (Phase 14.3) — mechanical fallback when both LLM
      providers are unavailable at lock time.  Average of skill-assessment
      signal strengths, capped at 0.5, confidence = 0.3.

    Unique constraint on (practitioner_id, certification_domain_id) so there
    is at most one score row per practitioner × domain — the agent upserts.
    """

    __tablename__ = "certification_domain_scores"

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    practitioner_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("practitioners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    certification_domain_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("certification_domains.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mastery_score: Mapped[float] = mapped_column(
        sa.Numeric(4, 3), nullable=False, comment="0–1 domain readiness estimate"
    )
    confidence: Mapped[float] = mapped_column(
        sa.Numeric(4, 3),
        nullable=False,
        comment="0–1 confidence; capped at 0.5 for self_assessment_estimate",
    )
    # self_assessment_estimate | quiz_derived
    source: Mapped[str] = mapped_column(sa.String(30), nullable=False)
    last_computed_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        default=_now_utc,
        nullable=False,
    )
    # Phase 10.3: score from the previous compute cycle, for delta / trend display.
    previous_mastery_score: Mapped[float | None] = mapped_column(
        sa.Numeric(4, 3), nullable=True
    )

    practitioner: Mapped["Practitioner"] = relationship(
        back_populates="certification_domain_scores"
    )
    domain: Mapped["CertificationDomain"] = relationship(
        back_populates="domain_scores"
    )

    __table_args__ = (
        sa.CheckConstraint(
            "mastery_score >= 0 AND mastery_score <= 1",
            name="ck_cert_domain_scores_mastery",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_cert_domain_scores_confidence",
        ),
        sa.CheckConstraint(
            "source IN ('self_assessment_estimate','quiz_derived','degraded_estimate')",
            name="ck_cert_domain_scores_source",
        ),
        sa.UniqueConstraint(
            "practitioner_id",
            "certification_domain_id",
            name="uq_cert_domain_scores_practitioner_domain",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<CertificationDomainScore practitioner={self.practitioner_id!r} "
            f"domain={self.certification_domain_id!r} score={self.mastery_score} "
            f"source={self.source!r}>"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 5 — Auth tables
# ═══════════════════════════════════════════════════════════════════════════════


# ── admin_users ───────────────────────────────────────────────────────────────

class AdminUser(Base):
    """Admin / leadership accounts — completely separate from practitioners.

    Every new row is seeded with must_change_password=True and password "welcome".
    role = "admin" has full access; role = "leadership" sees aggregates only.
    """

    __tablename__ = "admin_users"

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(
        sa.String(255), nullable=False, unique=True, index=True
    )
    first_name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    # "admin" (full access) | "leadership" (aggregates only)
    role: Mapped[str] = mapped_column(sa.String(30), nullable=False, default="admin")
    must_change_password: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        default=_now_utc,
        nullable=False,
    )
    # Phase 22: org membership — nullable FK to organizations
    organization_id: Mapped[str | None] = mapped_column(
        sa.String(36),
        sa.ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    organization: Mapped["Organization | None"] = relationship(
        back_populates="admin_users",
        foreign_keys="[AdminUser.organization_id]",
    )

    sessions: Mapped[list["Session"]] = relationship(
        back_populates="admin_user", cascade="all, delete-orphan"
    )

    __table_args__ = (
        sa.CheckConstraint(
            "role IN ('admin','leadership')",
            name="ck_admin_users_role",
        ),
    )

    def __repr__(self) -> str:
        return f"<AdminUser id={self.id!r} email={self.email!r} role={self.role!r}>"


# ── sessions ──────────────────────────────────────────────────────────────────

class Session(Base):
    """Server-side session table. The browser holds only the opaque UUID cookie.

    identity_type = "practitioner" → practitioner_id is set, admin_user_id is null.
    identity_type = "admin"        → admin_user_id is set, practitioner_id is null.

    Practitioner sessions never expire (last_seen_at updated on each request).
    Admin sessions expire after settings.admin_session_timeout_hours of inactivity
    (checked by get_session dependency; the row is deleted on expiry).
    """

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    # "practitioner" | "admin"
    identity_type: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    practitioner_id: Mapped[str | None] = mapped_column(
        sa.String(36),
        sa.ForeignKey("practitioners.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    admin_user_id: Mapped[str | None] = mapped_column(
        sa.String(36),
        sa.ForeignKey("admin_users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        default=_now_utc,
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        default=_now_utc,
        nullable=False,
    )
    # None for practitioners (no expiry); set to created_at + timeout for admins / product_admins
    expires_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    # Phase 22: product admin sessions
    product_admin_user_id: Mapped[str | None] = mapped_column(
        sa.String(36),
        sa.ForeignKey("product_admin_users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    admin_user: Mapped["AdminUser | None"] = relationship(back_populates="sessions")

    __table_args__ = (
        sa.CheckConstraint(
            "identity_type IN ('practitioner','admin','product_admin')",
            name="ck_sessions_identity_type",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Session id={self.id!r} type={self.identity_type!r} "
            f"practitioner={self.practitioner_id!r} admin={self.admin_user_id!r}>"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 6 — Practitioner Profiles
# ═══════════════════════════════════════════════════════════════════════════════


class PractitionerProfile(Base):
    """A practitioner's saved learning profile — background + cert goal + skill ratings."""

    __tablename__ = "practitioner_profiles"

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    practitioner_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("practitioners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    # Phase 9.3: locked once skill-assessments are first saved via the full wizard.
    # A locked profile cannot be edited or re-rated; only activation and deletion
    # are still permitted.  Defaults to False so existing profiles stay editable.
    is_locked: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    # Optional: which certification this profile is targeting
    certification_id: Mapped[str | None] = mapped_column(
        sa.String(36),
        sa.ForeignKey("certifications.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Phase 14.4: tracks the quality of domain scoring at profile-lock time.
    # 'pending'   — Domain Scorer has not run yet (default for new profiles).
    # 'lm_scored' — Domain Scorer ran successfully via primary or fallback LLM.
    # 'degraded'  — Both providers failed; scores computed mechanically from
    #               self-assessment signal strengths (confidence cap 0.3).
    domain_scoring_status: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        server_default="pending",
        default="pending",
    )
    # Phase 10.2: frozen at profile-lock time (Step 10.5) to the then-current
    # domain version for the chosen certification.  All domain scoring for this
    # profile — initial self-assessment estimates and quiz-derived scores —
    # uses certification_domains rows filtered to this version.  A subsequent
    # admin refresh never retroactively shifts this practitioner's baseline.
    # Null for profiles created before Step 10.5 runs.
    domain_version_id: Mapped[str | None] = mapped_column(
        sa.String(36),
        sa.ForeignKey("certification_domain_versions.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    # Verbatim questionnaire snapshot at save time
    # Use sa.JSON for cross-database compatibility (JSONB is Postgres-only but the
    # migration uses JSONB directly for the DDL — sa.JSON just handles the Python side)
    questionnaire_snapshot: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        default=_now_utc,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        default=_now_utc,
        nullable=False,
    )
    # Phase 22: soft-delete — set to now() instead of deleting the row
    deleted_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )

    practitioner: Mapped["Practitioner"] = relationship(back_populates="profiles")
    certification: Mapped["Certification | None"] = relationship()
    domain_version: Mapped["CertificationDomainVersion | None"] = relationship(
        back_populates="locked_profiles",
        foreign_keys=[domain_version_id],
    )
    skill_assessments: Mapped[list["ProfileSkillAssessment"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<PractitionerProfile id={self.id!r} practitioner={self.practitioner_id!r} "
            f"name={self.name!r} active={self.is_active}>"
        )


class ProfileSkillAssessment(Base):
    """Per-skill rating for a specific profile — upserted on re-save."""

    __tablename__ = "profile_skill_assessments"

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    profile_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("practitioner_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    signal_strength: Mapped[float] = mapped_column(sa.Numeric(4, 3), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        default=_now_utc,
        nullable=False,
    )

    profile: Mapped["PractitionerProfile"] = relationship(back_populates="skill_assessments")
    skill: Mapped["Skill"] = relationship()

    __table_args__ = (
        sa.UniqueConstraint("profile_id", "skill_id", name="uq_profile_skill_assessments"),
        sa.CheckConstraint(
            "signal_strength >= 0 AND signal_strength <= 1",
            name="ck_profile_skill_assessments_signal_strength",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ProfileSkillAssessment profile={self.profile_id!r} "
            f"skill={self.skill_id!r} signal={self.signal_strength}>"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 11 — Mock Exam tables
# ═══════════════════════════════════════════════════════════════════════════════


class MockExamSession(Base):
    """One exam sitting per practitioner — supports pause/resume.

    Status lifecycle: in_progress → paused → in_progress → completed.
    ``time_elapsed_seconds`` accumulates wall-clock seconds each time the
    session is paused.  ``last_resumed_at`` is set on every resume so the
    client can compute live elapsed time without polling.
    """

    __tablename__ = "mock_exam_sessions"

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    practitioner_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("practitioners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    certification_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("certifications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # generating | in_progress | paused | completed | failed | abandoned
    status: Mapped[str] = mapped_column(
        sa.String(20), nullable=False, default="generating",
        server_default="generating",
    )
    # Cumulative elapsed seconds before the last pause
    time_elapsed_seconds: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=0, server_default=sa.text("0")
    )
    # Set on resume; cleared on pause
    last_resumed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    # null until completed (0.000–1.000)
    score: Mapped[float | None] = mapped_column(sa.Numeric(4, 3), nullable=True)
    correct_count: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    total_count: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False,
        server_default=sa.text("now()"), default=_now_utc,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    # Phase 19 — abandonment
    abandoned_reason: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    abandoned_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False,
        server_default=sa.text("now()"), default=_now_utc,
    )

    practitioner: Mapped["Practitioner"] = relationship()
    certification: Mapped["Certification"] = relationship(back_populates="mock_exam_sessions")
    questions: Mapped[list["MockExamQuestion"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="MockExamQuestion.sequence_order",
    )

    __table_args__ = (
        sa.CheckConstraint(
            "status IN ('generating','in_progress','paused','completed','failed','abandoned')",
            name="ck_mock_exam_sessions_status",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<MockExamSession id={self.id!r} practitioner={self.practitioner_id!r} "
            f"status={self.status!r}>"
        )


class MockExamQuestion(Base):
    """One MCQ row for a mock exam session.

    ``answer_key`` stores the full options + correct_index + trap_index so the
    session is self-contained even if the generating agent is unavailable later.
    ``response`` is null until the practitioner answers; ``score`` is 0 or 1.
    """

    __tablename__ = "mock_exam_questions"

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("mock_exam_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence_order: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    certification_domain_name: Mapped[str | None] = mapped_column(
        sa.String(200), nullable=True
    )
    skill_name: Mapped[str | None] = mapped_column(sa.String(200), nullable=True)
    prompt: Mapped[str] = mapped_column(sa.Text, nullable=False)
    # {options: [...], correct_index: N, trap_index: N | null}
    answer_key: Mapped[dict] = mapped_column(sa.JSON, nullable=False)
    trap_explanation: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    difficulty: Mapped[float] = mapped_column(sa.Numeric(4, 3), nullable=False)
    # null until answered — {selected_index: N}
    response: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    # null until answered — 0.0 or 1.0 for MCQ
    score: Mapped[float | None] = mapped_column(sa.Numeric(4, 3), nullable=True)
    answered_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )

    session: Mapped["MockExamSession"] = relationship(back_populates="questions")

    def __repr__(self) -> str:
        return (
            f"<MockExamQuestion id={self.id!r} session={self.session_id!r} "
            f"order={self.sequence_order} answered={self.answered_at is not None}>"
        )


# ── byte_sized_lessons ────────────────────────────────────────────────────────

class ByteSizedLesson(Base):
    """AI-generated micro-content per skill gap, one per skill per path generation."""

    __tablename__ = "byte_sized_lessons"

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    practitioner_id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("practitioners.id", ondelete="CASCADE"), nullable=False, index=True
    )
    learning_path_id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("skills.id", ondelete="CASCADE"), nullable=False
    )
    skill_name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    gap_pct: Mapped[float] = mapped_column(sa.Float, nullable=False)
    target_pct: Mapped[float] = mapped_column(sa.Float, nullable=False, server_default="0.85", default=0.85)
    what_missing: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    content_md: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    external_links: Mapped[list | None] = mapped_column(sa.JSON, nullable=True)
    estimated_read_minutes: Mapped[int | None] = mapped_column(sa.SmallInteger, nullable=True)
    path_generation_seq: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    generation_status: Mapped[str] = mapped_column(
        sa.String(20), nullable=False, server_default="pending", default="pending"
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.text("now()"), default=_now_utc, nullable=False
    )

    practitioner: Mapped["Practitioner"] = relationship(back_populates="byte_sized_lessons")
    reads: Mapped[list["LessonRead"]] = relationship(back_populates="lesson", cascade="all, delete-orphan")


class LessonRead(Base):
    """Tracks when a practitioner opens and closes a lesson modal."""

    __tablename__ = "lesson_reads"

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    lesson_id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("byte_sized_lessons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    practitioner_id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("practitioners.id", ondelete="CASCADE"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    duration_seconds: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.text("now()"), default=_now_utc, nullable=False
    )

    lesson: Mapped["ByteSizedLesson"] = relationship(back_populates="reads")


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 22 — Multi-Tenant SaaS tables
# ═══════════════════════════════════════════════════════════════════════════════


class SubscriptionPlan(Base):
    """Tiered subscription plan — one row per plan SKU."""

    __tablename__ = "subscription_plans"

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    # free | paid | enterprise
    tier: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    max_profiles_per_practitioner: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    max_learning_paths: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    max_mock_exams_per_profile: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    max_practitioners_per_org: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    allow_cert_recycling: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    nudges_enabled: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    teams_notifications_enabled: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.text("now()"), default=_now_utc, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.text("now()"), default=_now_utc, nullable=False
    )

    organizations: Mapped[list["Organization"]] = relationship(back_populates="plan")

    __table_args__ = (
        sa.CheckConstraint("tier IN ('free','paid','enterprise')", name="ck_subscription_plans_tier"),
    )

    def __repr__(self) -> str:
        return f"<SubscriptionPlan id={self.id!r} name={self.name!r} tier={self.tier!r}>"


class Organization(Base):
    """A tenant org — maps practitioners and admins to a subscription plan."""

    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    plan_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("subscription_plans.id", ondelete="RESTRICT"),
        nullable=False,
    )
    billing_email: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.text("now()"), default=_now_utc, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.text("now()"), default=_now_utc, nullable=False
    )

    plan: Mapped["SubscriptionPlan"] = relationship(back_populates="organizations")
    enrollment_codes: Mapped[list["OrgEnrollmentCode"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    notification_settings: Mapped["OrgNotificationSettings | None"] = relationship(
        back_populates="organization", uselist=False, cascade="all, delete-orphan"
    )
    practitioners: Mapped[list["Practitioner"]] = relationship(
        back_populates="organization", foreign_keys="[Practitioner.organization_id]"
    )
    admin_users: Mapped[list["AdminUser"]] = relationship(
        back_populates="organization", foreign_keys="[AdminUser.organization_id]"
    )

    def __repr__(self) -> str:
        return f"<Organization id={self.id!r} name={self.name!r}>"


class OrgEnrollmentCode(Base):
    """One-time-use enrollment code for joining an organization."""

    __tablename__ = "org_enrollment_codes"

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(sa.String(16), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.text("now()"), default=_now_utc, nullable=False
    )

    organization: Mapped["Organization"] = relationship(back_populates="enrollment_codes")

    __table_args__ = (
        sa.CheckConstraint("length(code) = 16", name="ck_org_enrollment_codes_length"),
    )

    def __repr__(self) -> str:
        return f"<OrgEnrollmentCode id={self.id!r} org={self.organization_id!r}>"


class ProductAdminUser(Base):
    """Super-admin who manages the entire platform — separate from per-org AdminUser."""

    __tablename__ = "product_admin_users"

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(
        sa.String(255), nullable=False, unique=True, index=True
    )
    password_hash: Mapped[str] = mapped_column(sa.Text, nullable=False)
    first_name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    must_change_password: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    # Phase 22 follow-up: 30-day rotation policy.  Set to now() on every
    # successful change-password call.  NULL = never changed voluntarily
    # (seeded or first-login flow not yet completed).
    password_changed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.text("now()"), default=_now_utc, nullable=False
    )

    def __repr__(self) -> str:
        return f"<ProductAdminUser id={self.id!r} email={self.email!r}>"


class OrgNotificationSettings(Base):
    """Microsoft Teams / email notification settings per organization — Phase 22."""

    __tablename__ = "org_notification_settings"

    organization_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("organizations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    teams_webhook_url: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    teams_channel_name: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    email_enabled: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.text("now()"), default=_now_utc, nullable=False
    )

    organization: Mapped["Organization"] = relationship(back_populates="notification_settings")

    def __repr__(self) -> str:
        return f"<OrgNotificationSettings org={self.organization_id!r}>"
