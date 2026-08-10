"""Generate SQL INSERT statements for the certification catalog (and supporting data).

No database connection required — reads directly from the constants in generate.py
and writes a self-contained .sql file you can paste into Supabase's SQL Editor.

Usage (from backend/):
    py -m seed.generate_sql
"""

import uuid
import sys
from datetime import date
from pathlib import Path

# Pull constants from generate.py without importing the async/SQLAlchemy parts
import importlib.util, types

# ── Inline the constants from generate.py ────────────────────────────────────

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

SKILL_TREE = [
    {"name": "AI Foundations", "category": "AI Foundations", "parent": None,
     "desc": "Core concepts of artificial intelligence and machine learning."},
    {"name": "Prompt Engineering", "category": "AI Foundations", "parent": "AI Foundations",
     "desc": "Crafting effective prompts for language models."},
    {"name": "AI Ethics & Safety", "category": "AI Foundations", "parent": "AI Foundations",
     "desc": "Responsible AI development and deployment principles."},
    {"name": "Evaluating LLM Output", "category": "AI Foundations", "parent": "AI Foundations",
     "desc": "Techniques for assessing the quality of model responses."},
    {"name": "Claude API", "category": "Claude API", "parent": None,
     "desc": "Working with the Anthropic Claude API."},
    {"name": "Structured Outputs", "category": "Claude API", "parent": "Claude API",
     "desc": "Using JSON schemas and Pydantic models to enforce typed responses."},
    {"name": "Tool Use & Function Calling", "category": "Claude API", "parent": "Claude API",
     "desc": "Implementing and calling tools within a Claude conversation."},
    {"name": "Context & Caching", "category": "Claude API", "parent": "Claude API",
     "desc": "Prompt caching, context window management, and token efficiency."},
    {"name": "Agentic AI", "category": "Agentic AI", "parent": None,
     "desc": "Building autonomous AI agents and multi-agent systems."},
    {"name": "MCP Servers", "category": "Agentic AI", "parent": "Agentic AI",
     "desc": "Building and consuming Model Context Protocol servers."},
    {"name": "Orchestration Patterns", "category": "Agentic AI", "parent": "Agentic AI",
     "desc": "Workflow design for multi-step agent pipelines."},
    {"name": "Agent Observability", "category": "Agentic AI", "parent": "Agentic AI",
     "desc": "Tracing, logging, and debugging AI agent runs."},
    {"name": "MLOps", "category": "MLOps", "parent": None,
     "desc": "Operations and lifecycle management for ML systems."},
    {"name": "Model Deployment", "category": "MLOps", "parent": "MLOps",
     "desc": "Packaging and serving ML models in production environments."},
    {"name": "Monitoring & Drift Detection", "category": "MLOps", "parent": "MLOps",
     "desc": "Tracking model performance and detecting data/concept drift."},
    {"name": "CI/CD for ML", "category": "MLOps", "parent": "MLOps",
     "desc": "Automating training, evaluation, and deployment pipelines."},
]


# ── SQL generation helpers ────────────────────────────────────────────────────

def q(value) -> str:
    """Quote a string value for SQL, or return NULL."""
    if value is None:
        return "NULL"
    # Escape single quotes
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def b(value: bool) -> str:
    return "TRUE" if value else "FALSE"


def gen_sql() -> str:
    today = date.today().isoformat()
    lines = []
    lines.append("-- ============================================================")
    lines.append("-- Mastery Pulse — Certification Catalog Seed")
    lines.append(f"-- Generated: {today}")
    lines.append("-- Paste into Supabase SQL Editor and click Run.")
    lines.append("-- Safe to re-run: deletes existing seed rows first.")
    lines.append("-- ============================================================")
    lines.append("")

    # Assign UUIDs upfront so they're consistent across insert sections
    skill_ids: dict[str, str] = {s["name"]: str(uuid.uuid4()) for s in SKILL_TREE}
    provider_ids: dict[str, str] = {p["name"]: str(uuid.uuid4()) for p in CERTIFICATION_PROVIDERS}
    cert_ids: dict[str, str] = {c["code"]: str(uuid.uuid4()) for c in CERTIFICATIONS_SEED}

    cert_codes_sql = ", ".join(q(c["code"]) for c in CERTIFICATIONS_SEED)
    provider_names_sql = ", ".join(q(p["name"]) for p in CERTIFICATION_PROVIDERS)
    child_names_sql = ", ".join(q(s["name"]) for s in SKILL_TREE if s["parent"] is not None)
    parent_names_sql = ", ".join(q(s["name"]) for s in SKILL_TREE if s["parent"] is None)

    # ── 1. Deletes in FK-safe order ──────────────────────────────────────
    # certification_skills → certifications → certification_providers → skills (children → parents)
    lines.append("-- 1. Deletes (FK-safe order: most-dependent first)")
    lines.append(
        f"DELETE FROM certification_skills WHERE certification_id IN "
        f"(SELECT id FROM certifications WHERE code IN ({cert_codes_sql}));"
    )
    lines.append(f"DELETE FROM certifications WHERE code IN ({cert_codes_sql});")
    lines.append(f"DELETE FROM certification_providers WHERE name IN ({provider_names_sql});")
    lines.append(f"DELETE FROM skills WHERE name IN ({child_names_sql});")
    lines.append(f"DELETE FROM skills WHERE name IN ({parent_names_sql});")
    lines.append("")

    # ── 2. Skills ────────────────────────────────────────────────────────
    lines.append("-- 2. Skills (parents first, then children)")

    # Parent skills first
    for spec in SKILL_TREE:
        if spec["parent"] is not None:
            continue
        lines.append(
            f"INSERT INTO skills (id, name, category, parent_skill_id, description) VALUES "
            f"({q(skill_ids[spec['name']])}, {q(spec['name'])}, {q(spec['category'])}, NULL, {q(spec['desc'])});"
        )

    lines.append("")

    # Child skills (reference parent IDs inline)
    for spec in SKILL_TREE:
        if spec["parent"] is None:
            continue
        parent_id = skill_ids[spec["parent"]]
        lines.append(
            f"INSERT INTO skills (id, name, category, parent_skill_id, description) VALUES "
            f"({q(skill_ids[spec['name']])}, {q(spec['name'])}, {q(spec['category'])}, {q(parent_id)}, {q(spec['desc'])});"
        )

    lines.append("")

    # ── 3. Certification providers ───────────────────────────────────────
    lines.append("-- 3. Certification providers")

    for pspec in CERTIFICATION_PROVIDERS:
        lines.append(
            f"INSERT INTO certification_providers (id, name, website, notes) VALUES "
            f"({q(provider_ids[pspec['name']])}, {q(pspec['name'])}, {q(pspec.get('website'))}, {q(pspec.get('notes'))});"
        )

    lines.append("")

    # ── 4. Certifications ────────────────────────────────────────────────
    lines.append("-- 4. Certifications")

    for cspec in CERTIFICATIONS_SEED:
        cid = cert_ids[cspec["code"]]
        pid = provider_ids[cspec["provider"]]
        lines.append(
            f"INSERT INTO certifications "
            f"(id, provider_id, code, name, level, requires_coding_background, "
            f"typical_audience, focus_area, exam_format, eligibility_notes, "
            f"external_url, is_active, last_verified_at) VALUES ("
            f"{q(cid)}, {q(pid)}, {q(cspec['code'])}, {q(cspec['name'])}, "
            f"{q(cspec['level'])}, {b(cspec['requires_coding_background'])}, "
            f"{q(cspec.get('typical_audience'))}, {q(cspec.get('focus_area'))}, "
            f"{q(cspec.get('exam_format'))}, {q(cspec.get('eligibility_notes'))}, "
            f"{q(cspec.get('external_url'))}, TRUE, {q(today)});"
        )

    lines.append("")

    # ── 4. certification_skills ──────────────────────────────────────────
    lines.append("-- 4. Certification–skill mappings")
    for cspec in CERTIFICATIONS_SEED:
        cid = cert_ids[cspec["code"]]
        for skill_name, weight in cspec["skill_weights"].items():
            sid = skill_ids.get(skill_name)
            if sid is None:
                lines.append(f"-- WARNING: skill '{skill_name}' not found, skipped")
                continue
            lines.append(
                f"INSERT INTO certification_skills (certification_id, skill_id, weight) VALUES "
                f"({q(cid)}, {q(sid)}, {round(weight, 3)});"
            )

    lines.append("")

    # ── 5. Verification query ────────────────────────────────────────────
    lines.append("-- 5. Verify")
    lines.append("SELECT p.name AS provider, c.code, c.name, c.level, c.requires_coding_background")
    lines.append("FROM certifications c")
    lines.append("JOIN certification_providers p ON p.id = c.provider_id")
    lines.append("ORDER BY p.name, c.code;")
    lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    sql = gen_sql()
    out_path = Path(__file__).parent / "seed_catalog.sql"
    out_path.write_text(sql, encoding="utf-8")
    print(f"Written to {out_path}")
    print()
    print("─" * 60)
    print(sql)
