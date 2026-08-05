"""SQLAlchemy ORM models.

Phase 0 tables: practitioners, skills, skill_profile_events,
skill_profile_snapshots, agent_runs, workflow_runs.

Phase 2 tables: certification_providers, certifications, certification_skills,
practitioner_certification_goals, certification_advisor_responses,
learning_paths, learning_path_items, items, attempts.
"""

import uuid
from datetime import UTC, date, datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
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
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        default=_now_utc,
        nullable=False,
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
            "source IN ('certification','self_assessment','quiz_attempt','project_history')",
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

    provider: Mapped["CertificationProvider"] = relationship(back_populates="certifications")
    certification_skills: Mapped[list["CertificationSkill"]] = relationship(
        back_populates="certification", cascade="all, delete-orphan"
    )
    practitioner_goals: Mapped[list["PractitionerCertificationGoal"]] = relationship(
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

    certification: Mapped["Certification"] = relationship(back_populates="certification_skills")
    skill: Mapped["Skill"] = relationship()

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

    skill: Mapped["Skill"] = relationship()
    attempts: Mapped[list["Attempt"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
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

    practitioner: Mapped["Practitioner"] = relationship(back_populates="nudges")

    __table_args__ = (
        sa.CheckConstraint(
            "nudge_type IN ('gap_alert','encouragement','reminder')",
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

class Rollup(Base):
    """Leadership-facing aggregate — never keyed to an individual.

    The min_cohort_size_met boolean is a structural privacy control, not a
    display-layer check. If False, metrics and narrative are not populated.
    See docs/human-in-the-loop.md for the policy rationale.
    """

    __tablename__ = "rollups"

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=_uuid)
    # team | practice
    scope: Mapped[str] = mapped_column(sa.String(30), nullable=False)
    # Identifies which team or practice (not an individual FK — by design)
    scope_ref: Mapped[str] = mapped_column(sa.String(255), nullable=False, index=True)
    period_start: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    # Populated only when min_cohort_size_met is True
    metrics: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    narrative: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    # Structural privacy gate — if False, metrics/narrative are withheld
    min_cohort_size_met: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False,
        server_default=sa.text("now()"), default=_now_utc,
    )

    __table_args__ = (
        sa.CheckConstraint(
            "scope IN ('team','practice')",
            name="ck_rollups_scope",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Rollup id={self.id!r} scope={self.scope!r} ref={self.scope_ref!r} "
            f"cohort_met={self.min_cohort_size_met}>"
        )
