"""SQLAlchemy ORM models.

Phase 0 includes: practitioners, skills, skill_profile_events,
skill_profile_snapshots, agent_runs, workflow_runs.

Later phases add certifications, items, attempts, nudges, rollups, etc. —
introduced as separate, smaller migrations to stay easy to reason about and reverse.
"""

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> str:
    return str(uuid.uuid4())


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
        nullable=False,
    )

    # Relationships (back-populated as later phases add tables)
    skill_profile_events: Mapped[list["SkillProfileEvent"]] = relationship(
        back_populates="practitioner", cascade="all, delete-orphan"
    )
    skill_profile_snapshots: Mapped[list["SkillProfileSnapshot"]] = relationship(
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
            "status IN ('running','completed','failed')",
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
