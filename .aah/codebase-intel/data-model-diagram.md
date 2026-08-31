# Data Model

## Overview
The database uses PostgreSQL (async via `asyncpg`). The schema grew across 22 phases and is managed by Alembic. Core entities revolve around `practitioners` (users), `certifications` (the goal domain), `skills` (the graph they're rated against), `practitioner_profiles` (a locked snapshot per cert goal), `items` (LLM-generated practice questions), and `nudges` (coach messages). Phase 22 added full multi-tenancy via `organizations`, `subscription_plans`, and `product_admin_users`.

## Entity Relationship Diagram

```mermaid
erDiagram
    SUBSCRIPTION_PLANS {
        string id PK
        string name UK
        string tier "free | pro | enterprise"
        int max_practitioners
        boolean domain_discovery_enabled
    }

    ORGANIZATIONS {
        string id PK
        string name
        string plan_id FK
        boolean is_active
        datetime created_at
    }

    PRACTITIONERS {
        string id PK
        string email UK
        string name
        string role
        string practice
        string seniority_level
        boolean is_active
        string organization_id FK
        datetime created_at
    }

    ADMIN_USERS {
        string id PK
        string email UK
        string first_name
        string password_hash
        string role "admin | leadership"
        boolean must_change_password
        string organization_id FK
        datetime created_at
    }

    PRODUCT_ADMIN_USERS {
        string id PK
        string email UK
        string password_hash
        datetime created_at
    }

    SESSIONS {
        string id PK
        string identity_type "practitioner | admin | product_admin"
        string practitioner_id FK
        string admin_user_id FK
        string product_admin_user_id FK
        datetime expires_at
        datetime last_seen_at
    }

    SKILLS {
        string id PK
        string name
        string category
        string parent_skill_id FK
        text description
    }

    CERTIFICATION_PROVIDERS {
        string id PK
        string name UK
        string website
    }

    CERTIFICATIONS {
        string id PK
        string provider_id FK
        string code UK
        string name
        string level "foundational | associate | professional | specialty | expert"
        boolean requires_coding_background
        int exam_question_count
        int exam_duration_minutes
        decimal exam_passing_score_pct
        boolean is_active
    }

    CERTIFICATION_DOMAIN_VERSIONS {
        string id PK
        string certification_id FK
        string version_label
        boolean is_current
        string source_notes
        datetime created_at
    }

    CERTIFICATION_DOMAINS {
        string id PK
        string certification_id FK
        string domain_version_id FK
        text domain_name
        decimal weight_pct
        int sequence_order
    }

    CERTIFICATION_SKILLS {
        string certification_id PK-FK
        string skill_id PK-FK
        decimal weight
        string certification_domain_id FK
        string source "seed | agent_discovered"
    }

    PRACTITIONER_PROFILES {
        string id PK
        string practitioner_id FK
        string certification_id FK
        string domain_version_id FK
        string name
        boolean is_active
        boolean is_locked
        string domain_scoring_status "pending | lm_scored | degraded"
        datetime deleted_at
    }

    PROFILE_SKILL_ASSESSMENTS {
        string id PK
        string profile_id FK
        string skill_id FK
        decimal signal_strength
    }

    ITEMS {
        string id PK
        string skill_id FK
        string certification_domain_id FK
        string item_type "mcq | free_text | scenario"
        text prompt
        json answer_key
        text trap_explanation
        decimal difficulty
        boolean is_cert_evaluated
        int generation
    }

    ATTEMPTS {
        string id PK
        string practitioner_id FK
        string item_id FK
        json response
        decimal score
        text grader_rationale
        boolean is_trap_selected
    }

    LEARNING_PATHS {
        string id PK
        string practitioner_id FK
        string status "draft | active | completed"
        datetime generated_at
    }

    LEARNING_PATH_ITEMS {
        string id PK
        string learning_path_id FK
        string skill_id FK
        int sequence_order
        string resource_type "item_set | scenario_lab | external_reading"
        string status "pending | in_progress | done"
        string quiz_status "pending | ready | failed"
    }

    CERTIFICATION_DOMAIN_SCORES {
        string id PK
        string practitioner_id FK
        string certification_domain_id FK
        decimal mastery_score
        decimal confidence
        string source "self_assessment_estimate | quiz_derived | degraded_estimate"
        decimal previous_mastery_score
    }

    SKILL_PROFILE_SNAPSHOTS {
        string practitioner_id PK-FK
        string skill_id PK-FK
        decimal mastery_score
        decimal confidence
        datetime last_computed_at
    }

    NUDGES {
        string id PK
        string practitioner_id FK
        string nudge_type "gap_alert | encouragement | reminder | campaign"
        string channel "email | in_app"
        text content
        string status "drafted | approved | sent"
        boolean is_read
    }

    ORGANIZATIONS ||--o{ PRACTITIONERS : "enrolls"
    ORGANIZATIONS ||--o{ ADMIN_USERS : "has"
    SUBSCRIPTION_PLANS ||--o{ ORGANIZATIONS : "governs"
    PRACTITIONERS ||--o{ SESSIONS : "authenticates via"
    ADMIN_USERS ||--o{ SESSIONS : "authenticates via"
    PRACTITIONERS ||--o{ PRACTITIONER_PROFILES : "has"
    CERTIFICATIONS ||--o{ PRACTITIONER_PROFILES : "targeted by"
    CERTIFICATION_DOMAIN_VERSIONS ||--o{ PRACTITIONER_PROFILES : "locks"
    PRACTITIONER_PROFILES ||--o{ PROFILE_SKILL_ASSESSMENTS : "contains"
    SKILLS ||--o{ PROFILE_SKILL_ASSESSMENTS : "rated by"
    SKILLS ||--o{ CERTIFICATION_SKILLS : "mapped via"
    CERTIFICATIONS ||--o{ CERTIFICATION_SKILLS : "covers"
    CERTIFICATION_PROVIDERS ||--o{ CERTIFICATIONS : "issues"
    CERTIFICATIONS ||--o{ CERTIFICATION_DOMAIN_VERSIONS : "has"
    CERTIFICATION_DOMAIN_VERSIONS ||--o{ CERTIFICATION_DOMAINS : "defines"
    CERTIFICATION_DOMAINS ||--o{ CERTIFICATION_DOMAIN_SCORES : "scored by"
    PRACTITIONERS ||--o{ CERTIFICATION_DOMAIN_SCORES : "holds"
    PRACTITIONERS ||--o{ ITEMS : "via skill"
    SKILLS ||--o{ ITEMS : "covers"
    PRACTITIONERS ||--o{ ATTEMPTS : "submits"
    ITEMS ||--o{ ATTEMPTS : "answered by"
    PRACTITIONERS ||--o{ LEARNING_PATHS : "follows"
    LEARNING_PATHS ||--o{ LEARNING_PATH_ITEMS : "contains"
    PRACTITIONERS ||--o{ NUDGES : "receives"
```

## Key Entities

| Entity | Purpose | Key Fields | Relationships |
|--------|---------|------------|---------------|
| Practitioner | Platform user | email, name, role, is_active, organization_id | → profiles, attempts, nudges, learning_paths |
| Certification | Target credential | code, level, provider_id, exam_config | → domains, skills, practitioner_goals |
| PractitionerProfile | Locked cert+skill snapshot | is_locked, domain_scoring_status, domain_version_id | → skill_assessments, domain_scores |
| Item | Practice question | item_type, answer_key, trap_explanation, difficulty | → attempts, skill, certification_domain |
| CertificationDomainVersion | Exam domain snapshot | is_current, version_label, source_notes | → certification_domains, locked_profiles |
| Session | Auth session | identity_type, expires_at, last_seen_at | → practitioner/admin/product_admin |
| Nudge | Coach message | nudge_type, channel, status (drafted→approved→sent) | → practitioner, nudge_category |
| Organization | Tenant | plan_id, is_active | → practitioners, admin_users |

## Data Stores

| Store | Type | Purpose |
|-------|------|---------|
| PostgreSQL | Relational RDBMS | Primary data store for all entities; 22-phase Alembic migration history |
| pgvector | Postgres extension | Vector embeddings for potential semantic search (provisioned, not yet fully active) |
| SQLite (aiosqlite) | In-process | Unit test database — no Docker required; skips Postgres-only constraints |
