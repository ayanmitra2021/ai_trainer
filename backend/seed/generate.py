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
- Certification catalog: 4 Anthropic + 2 AWS + 2 Google Cloud + 2 Microsoft entries
"""

import asyncio
import random
import uuid
from datetime import date, datetime, timedelta, timezone

from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import delete, select

from app.config import settings
from app.db.models import (
    AdminUser,
    Certification,
    CertificationProvider,
    CertificationSkill,
    Practitioner,
    Skill,
    SkillProfileEvent,
)
from seed.certification_domains import seed_certification_domains

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

# ── Certification catalog ─────────────────────────────────────────────────────
# Source: docs/data-model.md § Seed catalog (Step 2.2)
# last_verified_at is set to today's date at seed time — update when re-verifying.

CERTIFICATION_PROVIDERS = [
    {
        "name": "Anthropic",
        "website": "https://www.anthropic.com/partners",
        "notes": (
            "Partner Network certifications — registration requires a partner-org email. "
            "Contact your Anthropic partner representative to access exam portals."
        ),
    },
    {
        "name": "AWS",
        "website": "https://aws.amazon.com/certification/",
        "notes": "Amazon Web Services certifications via AWS Training and Certification.",
    },
    {
        "name": "Google Cloud",
        "website": "https://cloud.google.com/certification",
        "notes": "Google Cloud certifications via Google Cloud Skills Boost.",
    },
    {
        "name": "Microsoft",
        "website": "https://learn.microsoft.com/en-us/certifications/",
        "notes": "Microsoft Azure certifications via Microsoft Learn.",
    },
]

# Each entry maps to a provider by name (resolved at seed time).
# skill_names: list of skill names from SKILL_TREE; weights sum guidance only.
CERTIFICATIONS_SEED = [
    # ── Anthropic ────────────────────────────────────────────────────────
    {
        "provider": "Anthropic",
        "code": "CCAO-F",
        "name": "Claude Certified Associate – Foundations",
        "level": "foundational",
        "requires_coding_background": False,
        "typical_audience": (
            "Business users, consultants, and productivity-focused practitioners "
            "who use Claude conversationally — not developers or agentic builders."
        ),
        "focus_area": "Effective use of Claude for business tasks; prompt fundamentals; AI ethics.",
        "exam_format": "Multiple-choice and short-response; no coding required.",
        "eligibility_notes": "Requires Anthropic Partner Network org email.",
        "external_url": None,
        "skill_weights": {
            "Prompt Engineering": 0.9,
            "AI Ethics & Safety": 0.8,
            "Evaluating LLM Output": 0.6,
        },
    },
    {
        "provider": "Anthropic",
        "code": "CCDV-F",
        "name": "Claude Certified Developer – Foundations",
        "level": "foundational",
        "requires_coding_background": True,
        "typical_audience": "Software developers building Claude-powered applications.",
        "focus_area": "Claude API integration; tool use; structured outputs; basic agent patterns.",
        "exam_format": "Multiple-choice and coding exercises.",
        "eligibility_notes": "Requires Anthropic Partner Network org email.",
        "external_url": None,
        "skill_weights": {
            "Structured Outputs": 0.9,
            "Tool Use & Function Calling": 0.8,
            "Prompt Engineering": 0.7,
            "Context & Caching": 0.6,
        },
    },
    {
        "provider": "Anthropic",
        "code": "CCAF",
        "name": "Claude Certified Architect – Foundations",
        "level": "foundational",
        "requires_coding_background": True,
        "typical_audience": "Technical architects designing Claude-powered systems at scale.",
        "focus_area": (
            "System design with Claude; agentic patterns; MCP; "
            "observability; multi-agent orchestration."
        ),
        "exam_format": "Scenario-based design questions; no live coding required.",
        "eligibility_notes": (
            "Technical background recommended. Requires Anthropic Partner Network org email."
        ),
        "external_url": None,
        "skill_weights": {
            "MCP Servers": 0.9,
            "Orchestration Patterns": 0.9,
            "Agent Observability": 0.8,
            "Structured Outputs": 0.7,
            "Tool Use & Function Calling": 0.7,
        },
    },
    {
        "provider": "Anthropic",
        "code": "CCAR-P",
        "name": "Claude Certified Architect – Professional",
        "level": "professional",
        "requires_coding_background": True,
        "typical_audience": (
            "Senior architects with hands-on production experience building "
            "complex Claude-powered systems."
        ),
        "focus_area": (
            "Advanced multi-agent design; security and compliance; cost optimisation; "
            "large-scale deployment patterns."
        ),
        "exam_format": "Scenario-based deep dives; architecture review exercises.",
        "eligibility_notes": (
            "CCAF recommended as prerequisite. Requires Anthropic Partner Network org email."
        ),
        "external_url": None,
        "skill_weights": {
            "Orchestration Patterns": 1.0,
            "Agent Observability": 0.9,
            "MCP Servers": 0.9,
            "Model Deployment": 0.7,
            "Monitoring & Drift Detection": 0.7,
        },
    },
    # ── AWS ──────────────────────────────────────────────────────────────
    {
        "provider": "AWS",
        "code": "AIF-C01",
        "name": "AWS Certified AI Practitioner",
        "level": "foundational",
        "requires_coding_background": False,
        "typical_audience": (
            "Business stakeholders, project managers, and non-technical practitioners "
            "working with AWS AI/ML services."
        ),
        "focus_area": "AWS AI/ML service landscape; responsible AI; basic ML concepts.",
        "exam_format": "65 questions; 90 minutes; Pearson VUE or testing centre.",
        "eligibility_notes": None,
        "external_url": "https://aws.amazon.com/certification/certified-ai-practitioner/",
        "skill_weights": {
            "Prompt Engineering": 0.7,
            "AI Ethics & Safety": 0.7,
            "Evaluating LLM Output": 0.5,
        },
    },
    {
        "provider": "AWS",
        "code": "MLA-C01",
        "name": "AWS Certified Machine Learning Engineer – Associate",
        "level": "associate",
        "requires_coding_background": True,
        "typical_audience": "ML engineers building, deploying, and monitoring models on AWS.",
        "focus_area": "SageMaker; MLOps pipelines; model deployment; monitoring.",
        "exam_format": "65 questions; 130 minutes; Pearson VUE or testing centre.",
        "eligibility_notes": "Recommended: 1+ year hands-on ML on AWS.",
        "external_url": "https://aws.amazon.com/certification/certified-machine-learning-engineer-associate/",
        "skill_weights": {
            "Model Deployment": 0.9,
            "Monitoring & Drift Detection": 0.8,
            "CI/CD for ML": 0.8,
        },
    },
    # ── Google Cloud ──────────────────────────────────────────────────────
    {
        "provider": "Google Cloud",
        "code": "GCGAIL",
        "name": "Google Cloud Generative AI Leader",
        "level": "foundational",
        "requires_coding_background": False,
        "typical_audience": (
            "Business leaders, strategists, and non-technical practitioners "
            "evaluating generative AI for their organisations."
        ),
        "focus_area": "GenAI strategy; responsible AI; Google Cloud AI product landscape.",
        "exam_format": "Multiple-choice; no coding.",
        "eligibility_notes": None,
        "external_url": "https://cloud.google.com/certification/generative-ai-leader",
        "skill_weights": {
            "Prompt Engineering": 0.7,
            "AI Ethics & Safety": 0.7,
        },
    },
    {
        "provider": "Google Cloud",
        "code": "GCPMLE",
        "name": "Professional Machine Learning Engineer",
        "level": "professional",
        "requires_coding_background": True,
        "typical_audience": "ML engineers designing, building, and productionising ML models on GCP.",
        "focus_area": "Vertex AI; MLOps on GCP; model monitoring; feature engineering.",
        "exam_format": "60 questions; 120 minutes; Pearson VUE or testing centre.",
        "eligibility_notes": "Recommended: 3+ years industry experience, 1+ year on GCP.",
        "external_url": "https://cloud.google.com/certification/machine-learning-engineer",
        "skill_weights": {
            "Model Deployment": 0.9,
            "Monitoring & Drift Detection": 0.9,
            "CI/CD for ML": 0.8,
        },
    },
    # ── Microsoft ─────────────────────────────────────────────────────────
    {
        "provider": "Microsoft",
        "code": "AI-900",
        "name": "Azure AI Fundamentals",
        "level": "foundational",
        "requires_coding_background": False,
        "typical_audience": (
            "Non-technical practitioners new to AI and Azure AI services."
        ),
        "focus_area": "Azure Cognitive Services; responsible AI; basic ML concepts.",
        "exam_format": "40–60 questions; 45 minutes; Pearson VUE.",
        "eligibility_notes": None,
        "external_url": "https://learn.microsoft.com/en-us/certifications/azure-ai-fundamentals/",
        "skill_weights": {
            "Prompt Engineering": 0.7,
            "AI Ethics & Safety": 0.6,
        },
    },
    {
        "provider": "Microsoft",
        "code": "AI-102",
        "name": "Azure AI Engineer Associate",
        "level": "associate",
        "requires_coding_background": True,
        "typical_audience": "Developers building Azure AI solutions using Cognitive Services and Azure OpenAI.",
        "focus_area": "Azure OpenAI integration; Cognitive Services; AI solution design.",
        "exam_format": "40–60 questions; 120 minutes; Pearson VUE.",
        "eligibility_notes": "Recommended: AI-900 or equivalent experience.",
        "external_url": "https://learn.microsoft.com/en-us/certifications/azure-ai-engineer/",
        "skill_weights": {
            "Tool Use & Function Calling": 0.7,
            "Prompt Engineering": 0.7,
            "AI Ethics & Safety": 0.6,
        },
    },
]


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

    # Delete in FK-safe order
    # certification_skills → certifications → providers (keyed by known provider names)
    provider_names = [p["name"] for p in CERTIFICATION_PROVIDERS]
    provider_ids_result = await session.execute(
        select(CertificationProvider.id).where(CertificationProvider.name.in_(provider_names))
    )
    provider_ids = [r[0] for r in provider_ids_result]
    if provider_ids:
        cert_ids_result = await session.execute(
            select(Certification.id).where(Certification.provider_id.in_(provider_ids))
        )
        cert_ids = [r[0] for r in cert_ids_result]
        if cert_ids:
            await session.execute(
                delete(CertificationSkill).where(
                    CertificationSkill.certification_id.in_(cert_ids)
                )
            )
        await session.execute(
            delete(Certification).where(Certification.provider_id.in_(provider_ids))
        )
    await session.execute(
        delete(CertificationProvider).where(CertificationProvider.name.in_(provider_names))
    )

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

    print("Inserting certification catalog...")
    verified_date = date.today()

    # Build providers
    provider_by_name: dict[str, CertificationProvider] = {}
    for pspec in CERTIFICATION_PROVIDERS:
        provider = CertificationProvider(
            id=str(uuid.uuid4()),
            name=pspec["name"],
            website=pspec.get("website"),
            notes=pspec.get("notes"),
        )
        session.add(provider)
        provider_by_name[pspec["name"]] = provider

    await session.flush()

    # Build certifications and skill mappings
    cert_count = 0
    for cspec in CERTIFICATIONS_SEED:
        provider = provider_by_name[cspec["provider"]]
        cert = Certification(
            id=str(uuid.uuid4()),
            provider_id=provider.id,
            code=cspec["code"],
            name=cspec["name"],
            level=cspec["level"],
            requires_coding_background=cspec["requires_coding_background"],
            typical_audience=cspec.get("typical_audience"),
            focus_area=cspec.get("focus_area"),
            exam_format=cspec.get("exam_format"),
            eligibility_notes=cspec.get("eligibility_notes"),
            external_url=cspec.get("external_url"),
            is_active=True,
            last_verified_at=verified_date,
        )
        session.add(cert)
        await session.flush()

        # Map to skills by name
        for skill_name, weight in cspec["skill_weights"].items():
            skill = skill_by_name.get(skill_name)
            if skill is None:
                print(f"  WARNING: skill '{skill_name}' not found for {cspec['code']}, skipping")
                continue
            cs = CertificationSkill(
                certification_id=cert.id,
                skill_id=skill.id,
                weight=round(weight, 3),
            )
            session.add(cs)
        cert_count += 1

    await session.commit()

    # ── Seed certification exam domains (Phase 10.1) ───────────────────────
    print("Inserting certification exam domains...")
    await seed_certification_domains(session)
    await session.commit()

    # ── Seed starter admin account ─────────────────────────────────────────
    print("Seeding starter admin account...")
    import bcrypt as _bcrypt_lib
    from sqlalchemy import select as sa_select

    ADMIN_EMAIL = "admin@example.com"

    existing_admin = (
        await session.execute(
            sa_select(AdminUser).where(AdminUser.email == ADMIN_EMAIL)
        )
    ).scalar_one_or_none()

    if existing_admin is None:
        pw_hash = _bcrypt_lib.hashpw(b"welcome", _bcrypt_lib.gensalt()).decode()
        starter_admin = AdminUser(
            id=str(uuid.uuid4()),
            email=ADMIN_EMAIL,
            first_name="Admin",
            password_hash=pw_hash,
            role="admin",
            must_change_password=True,
        )
        session.add(starter_admin)
        await session.commit()
        print(f"  Created admin: {ADMIN_EMAIL} / welcome (must change password)")
    else:
        print(f"  Admin already exists: {ADMIN_EMAIL} (skipped)")

    print(
        f"Done. Inserted {len(practitioners)} practitioners, "
        f"{len(all_skills)} skills, {events_added} events, "
        f"{len(CERTIFICATION_PROVIDERS)} providers, {cert_count} certifications."
    )


async def main() -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await seed(session)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
