"""Synthetic seed data generator.

Usage (from backend/):
    py -m seed.generate

Strategy: clear-then-seed — the script deletes all existing seed rows (keyed
by email domain @mastery.example) then inserts fresh ones. This makes re-runs
safe and idempotent without needing upsert logic on every table.

Produces:
- ~20 practitioners across several practices and seniority levels
- 16 skills in 4 categories (AI Foundations, Claude API, Agentic AI, MLOps)
  with a two-level hierarchy inside each category
- ~200 skill_profile_events spread across all four sources:
  certification | self_assessment | quiz_attempt | project_history
"""

import asyncio
import random
import uuid
from datetime import datetime, timedelta, timezone

from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import delete, select

from app.config import settings
from app.db.models import Practitioner, Skill, SkillProfileEvent

fake = Faker()
random.seed(42)
Faker.seed(42)

# ── Skill graph definition ────────────────────────────────────────────────────

SKILL_TREE: list[dict] = [
    # ── AI Foundations ────────────────────────────────────────────────────
    {"name": "AI Foundations", "category": "AI Foundations", "parent": None,
     "desc": "Core concepts of artificial intelligence and machine learning."},
    {"name": "Prompt Engineering", "category": "AI Foundations", "parent": "AI Foundations",
     "desc": "Crafting effective prompts for language models."},
    {"name": "AI Ethics & Safety", "category": "AI Foundations", "parent": "AI Foundations",
     "desc": "Responsible AI development and deployment principles."},
    {"name": "Evaluating LLM Output", "category": "AI Foundations", "parent": "AI Foundations",
     "desc": "Techniques for assessing the quality of model responses."},

    # ── Claude API ────────────────────────────────────────────────────────
    {"name": "Claude API", "category": "Claude API", "parent": None,
     "desc": "Working with the Anthropic Claude API."},
    {"name": "Structured Outputs", "category": "Claude API", "parent": "Claude API",
     "desc": "Using JSON schemas and Pydantic models to enforce typed responses."},
    {"name": "Tool Use & Function Calling", "category": "Claude API", "parent": "Claude API",
     "desc": "Implementing and calling tools within a Claude conversation."},
    {"name": "Context & Caching", "category": "Claude API", "parent": "Claude API",
     "desc": "Prompt caching, context window management, and token efficiency."},

    # ── Agentic AI ────────────────────────────────────────────────────────
    {"name": "Agentic AI", "category": "Agentic AI", "parent": None,
     "desc": "Building autonomous AI agents and multi-agent systems."},
    {"name": "MCP Servers", "category": "Agentic AI", "parent": "Agentic AI",
     "desc": "Building and consuming Model Context Protocol servers."},
    {"name": "Orchestration Patterns", "category": "Agentic AI", "parent": "Agentic AI",
     "desc": "Workflow design for multi-step agent pipelines."},
    {"name": "Agent Observability", "category": "Agentic AI", "parent": "Agentic AI",
     "desc": "Tracing, logging, and debugging AI agent runs."},

    # ── MLOps ─────────────────────────────────────────────────────────────
    {"name": "MLOps", "category": "MLOps", "parent": None,
     "desc": "Operations and lifecycle management for ML systems."},
    {"name": "Model Deployment", "category": "MLOps", "parent": "MLOps",
     "desc": "Packaging and serving ML models in production environments."},
    {"name": "Monitoring & Drift Detection", "category": "MLOps", "parent": "MLOps",
     "desc": "Tracking model performance and detecting data/concept drift."},
    {"name": "CI/CD for ML", "category": "MLOps", "parent": "MLOps",
     "desc": "Automating training, evaluation, and deployment pipelines."},
]

# ── Practitioner templates ────────────────────────────────────────────────────

PRACTICES = ["AI&E", "HCI", "T&T", "M&A"]
ROLES = [
    "Consultant", "Senior Consultant", "Manager",
    "Senior Manager", "Associate", "Specialist",
]
SENIORITY_LEVELS = ["junior", "mid", "senior", "lead", "principal"]

SEED_EMAIL_DOMAIN = "mastery.example"


def _seed_email(name: str) -> str:
    slug = name.lower().replace(" ", ".")
    return f"{slug}@{SEED_EMAIL_DOMAIN}"


PRACTITIONER_NAMES = [
    "Alex Rivera", "Jordan Kim", "Morgan Patel", "Casey Thompson", "Riley Nguyen",
    "Taylor Okafor", "Drew Santos", "Avery Chen", "Quinn Nakamura", "Sage Williams",
    "Rowan Martinez", "Blake Johnson", "Finley Davis", "Harley Wilson", "Reese Brown",
    "Cameron Lee", "Dakota Clark", "Emery White", "Hayden Hall", "Logan Turner",
]


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _days_ago(n: int) -> datetime:
    return _now_utc() - timedelta(days=n)


# ── Core generator ────────────────────────────────────────────────────────────

async def seed(session: AsyncSession) -> None:
    """Clear existing seed data and insert fresh rows."""
    print("Clearing existing seed data...")

    # Delete in FK-safe order (events → practitioners / skills)
    await session.execute(
        delete(SkillProfileEvent).where(
            SkillProfileEvent.practitioner_id.in_(
                select(Practitioner.id).where(
                    Practitioner.email.like(f"%@{SEED_EMAIL_DOMAIN}")
                )
            )
        )
    )
    await session.execute(
        delete(Practitioner).where(
            Practitioner.email.like(f"%@{SEED_EMAIL_DOMAIN}")
        )
    )
    # Skills are identified by name + category; delete in reverse hierarchy
    all_skill_names = [s["name"] for s in SKILL_TREE]
    # Delete children first, then parents
    child_names = [s["name"] for s in SKILL_TREE if s["parent"] is not None]
    parent_names = [s["name"] for s in SKILL_TREE if s["parent"] is None]
    await session.execute(
        delete(Skill).where(Skill.name.in_(child_names))
    )
    await session.execute(
        delete(Skill).where(Skill.name.in_(parent_names))
    )

    print("Inserting skills...")
    skill_by_name: dict[str, Skill] = {}

    # Insert parents first
    for spec in SKILL_TREE:
        if spec["parent"] is not None:
            continue
        skill = Skill(
            id=str(uuid.uuid4()),
            name=spec["name"],
            category=spec["category"],
            parent_skill_id=None,
            description=spec["desc"],
        )
        session.add(skill)
        skill_by_name[spec["name"]] = skill

    await session.flush()  # assign IDs so children can reference parents

    for spec in SKILL_TREE:
        if spec["parent"] is None:
            continue
        skill = Skill(
            id=str(uuid.uuid4()),
            name=spec["name"],
            category=spec["category"],
            parent_skill_id=skill_by_name[spec["parent"]].id,
            description=spec["desc"],
        )
        session.add(skill)
        skill_by_name[spec["name"]] = skill

    await session.flush()

    print("Inserting practitioners...")
    practitioners: list[Practitioner] = []
    for name in PRACTITIONER_NAMES:
        practitioner = Practitioner(
            id=str(uuid.uuid4()),
            name=name,
            email=_seed_email(name),
            role=random.choice(ROLES),
            practice=random.choice(PRACTICES),
            seniority_level=random.choice(SENIORITY_LEVELS),
        )
        session.add(practitioner)
        practitioners.append(practitioner)

    await session.flush()

    print("Inserting skill_profile_events...")
    all_skills = list(skill_by_name.values())
    sources = ["certification", "self_assessment", "quiz_attempt", "project_history"]

    # Ensure every source is represented (global guarantee) by seeding one
    # event per source for the first four practitioners before random sampling.
    events_added = 0
    for i, source in enumerate(sources):
        practitioner = practitioners[i]
        skill = random.choice(all_skills)
        event = SkillProfileEvent(
            id=str(uuid.uuid4()),
            practitioner_id=practitioner.id,
            skill_id=skill.id,
            source=source,
            signal_strength=round(random.uniform(0.3, 0.95), 3),
            occurred_at=_days_ago(random.randint(1, 180)),
            metadata_={"seeded": True, "source_guarantee": True},
        )
        session.add(event)
        events_added += 1

    # Random events to flesh out a realistic spread (~200 total)
    for practitioner in practitioners:
        n_events = random.randint(5, 15)
        for _ in range(n_events):
            source = random.choice(sources)
            skill = random.choice(all_skills)
            event = SkillProfileEvent(
                id=str(uuid.uuid4()),
                practitioner_id=practitioner.id,
                skill_id=skill.id,
                source=source,
                signal_strength=round(random.uniform(0.1, 1.0), 3),
                occurred_at=_days_ago(random.randint(1, 365)),
                metadata_={"seeded": True},
            )
            session.add(event)
            events_added += 1

    await session.commit()
    print(
        f"Done. Inserted {len(practitioners)} practitioners, "
        f"{len(all_skills)} skills, {events_added} events."
    )


async def main() -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await seed(session)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
