# Data Model — Mastery Pulse

Reference doc. Read this before touching migrations, or before building any agent that reads/writes these tables.

Single Postgres database, `pgvector` extension enabled (used by the Item-Writer agent for calibration/similarity, not required before Phase 2). Everything below is a sketch of purpose and relationships — exact column types, indexes, and constraints get decided when the migration is actually written (Step 0.2), not here.

## Design principles

- **Event-sourced signal, derived snapshot.** Raw signals (`skill_profile_events`, `usage_events`) are append-only and never updated in place. Agents compute derived state (`skill_profile_snapshots`, `correlation_snapshots`) from the event log. This is what makes the Correlation Agent's job possible — it needs history, not just a current value — and it means a bad snapshot can always be recomputed from source events instead of patched by hand.
- **Every agent call is audited.** `agent_runs` exists from Step 0.4 onward. No agent writes to business tables without a corresponding `agent_runs` row. This is the debugging and cost-tracking backbone for the whole system.
- **Privacy floor is structural, not a UI convention.** `rollups.min_cohort_size_met` is a real column, not a display-layer check — see `docs/human-in-the-loop.md` for why.

## Core tables

### `practitioners`
Who the system is about.
- `id`, `name`, `email`, `role` (e.g. "Senior Consultant"), `practice` (e.g. "HCI", "AI&E"), `seniority_level`, `created_at`

### `skills`
The skill graph both halves of the product share. Mastery Mesh measures against it; Adoption Pulse measures usage against it.
- `id`, `name`, `category`, `parent_skill_id` (self-FK, nullable — hierarchy), `description`

### `certification_providers`
Any certifying body — Anthropic, AWS, Google Cloud, Microsoft, or one added later. Nothing about the schema below assumes Anthropic specifically.
- `id`, `name`, `website` (nullable), `notes` (nullable)

### `certifications`
One row per credential, regardless of provider.
- `id`, `provider_id` (FK), `code` (e.g. `CCAO-F`, `AIF-C01`), `name`, `level` (`foundational` | `associate` | `professional` | `specialty` | `expert` — a normalized set that spans providers even though each names its own tiers differently), `requires_coding_background` (boolean), `typical_audience` (text, e.g. "business/productivity users, not developers"), `focus_area` (text), `exam_format` (text — length, question count, delivery), `eligibility_notes` (nullable text — e.g. a partner-network requirement), `external_url` (nullable), `is_active` (boolean), `last_verified_at` (date)

`last_verified_at` exists because this space moves fast — see the seed list below and the freshness note at the end of this doc.

### `certification_skills`
What a given certification actually covers, in terms of the skill graph above. This is what lets the Curriculum Planner weight a learning path toward a chosen certification instead of treating every skill as equally relevant.
- `certification_id` (FK), `skill_id` (FK), `weight` (numeric — how central this skill is to that exam)

### `certification_domains`
The official exam domains / modules for each certification — the concrete topics the exam actually tests, in the order and weighting the exam guide specifies. From Phase 10.2 onward these are versioned: each domain row belongs to a specific `certification_domain_version`, and a practitioner's profile is pinned to the version that was current at lock time.

They differ from `certification_skills` in specificity: `certification_skills` maps broad skill-graph nodes to a cert; `certification_domains` captures the actual sectioned content from the official exam guide (e.g. "Domain 2: Fundamentals of Generative AI — 24% of the exam").

- `id`, `certification_id` (FK → certifications), `domain_version_id` (FK → certification_domain_versions — which version snapshot this row belongs to; set on insert, never changed), `domain_name` (text — e.g. "Fundamentals of Generative AI"), `domain_description` (text — what the official guide says this domain covers), `weight_pct` (numeric — percentage of the exam, e.g. 24; all domains for one version for one cert must sum to 100), `sequence_order` (integer — matches the official exam guide ordering, used for display)

Seeded domains for each active cert (verified from official exam guides — see Step 10.1 and the 👤 flag in `docs/human-in-the-loop.md`):

| Cert | Domains |
|---|---|
| AIF-C01 | 1: Fundamentals of AI and ML (20%) · 2: Fundamentals of Generative AI (24%) · 3: Applications of Foundation Models (28%) · 4: Guidelines for Responsible AI (14%) · 5: Security, Compliance, and Governance for AI Solutions (14%) |
| CCAO-F | 1: Introduction to AI and Claude (20%) · 2: Prompt Engineering Fundamentals (25%) · 3: Claude API and Tool Use Essentials (20%) · 4: Responsible AI and Safety (20%) · 5: Deploying Claude in Practice (15%) |
| CCDV-F | 1: Claude API and SDK Essentials (25%) · 2: Advanced Prompt Engineering (20%) · 3: Tool Use and Function Calling (20%) · 4: Building and Testing Production Applications (20%) · 5: Evaluation and Monitoring (15%) |
| CCAF | 1: System Design with Claude (20%) · 2: Multi-Agent and Agentic Architectures (25%) · 3: RAG and Knowledge Integration (20%) · 4: Production Architecture Patterns (20%) · 5: Safety Engineering and Responsible Design (15%) |
| CCAR-P | 1: Advanced Agentic Systems at Scale (25%) · 2: Enterprise Integration Patterns (20%) · 3: Safety Engineering and Risk Management (20%) · 4: Performance Optimization and Cost Control (20%) · 5: Multi-Provider and Platform Strategies (15%) |
| AI-900 | 1: AI Workloads and Considerations (15–20%) · 2: Machine Learning in Azure (20–25%) · 3: Computer Vision Workloads (15–20%) · 4: Natural Language Processing Workloads (15–20%) · 5: Generative AI Workloads (15–20%) |
| AI-102 | 1: Plan and Manage an Azure AI Solution (15–20%) · 2: Implement Content Moderation Solutions (10–15%) · 3: Implement Computer Vision Solutions (15–20%) · 4: Implement NLP Solutions (30–35%) · 5: Implement Knowledge Mining and Document Intelligence (10–15%) · 6: Implement Generative AI Solutions (10–15%) |

> **Freshness note:** Domain weights shift when certs are revised. From Phase 10.3 onward, domain data is kept current via the Cert Domain Discovery Agent (admin-triggered, proposal-reviewed). The bootstrap seed from Phase 10.1 is version 1; every admin-approved refresh creates a new version in `certification_domain_versions`. Practitioners' existing scores are always anchored to the version in place when their profile was locked. Before Phase 10.3 is implemented, re-verify the seed file manually whenever a cert's `last_verified_at` is more than a few months old.

### `certification_domain_versions`
Tracks the history of exam domain data snapshots for each certification. Each version represents one approved point-in-time definition of the cert's domains. The bootstrap seed (Step 10.1) creates version 1 for each cert; subsequent admin refreshes via the Cert Domain Discovery Agent (Step 10.3) create new versions.

- `id`, `certification_id` (FK → certifications), `version_label` (text — e.g. "bootstrap-step-10.1" or "2025-Q1-refresh"), `is_current` (boolean — partial unique index on `(certification_id) WHERE is_current = true` enforces exactly one current version per cert at all times), `source_notes` (text — where the data came from: exam guide URL, agent confidence notes, or "bootstrap seed"), `agent_run_id` (nullable FK → agent_runs — null for bootstrap; set when an agent-driven refresh was the source), `created_by_admin_id` (nullable FK → admin_users — null for bootstrap), `created_at`

**Semantics on refresh:** when an admin approves a domain proposal (Step 10.4), the current version's `is_current` flips to false and the new version becomes `is_current = true`. Old domain rows for the superseded version are never deleted — profiles locked against them continue to reference them correctly.

### `certification_domain_proposals`
Pending domain refresh proposals produced by the Cert Domain Discovery Agent (Step 10.3). Each row represents one agent run's output for one certification, awaiting admin review. Approved proposals become new `certification_domain_versions` plus fresh `certification_domains` rows; rejected proposals are archived with a reason.

- `id`, `certification_id` (nullable FK → certifications — null when proposing a brand-new cert not yet in the catalog), `cert_code` (text), `cert_name` (text), `proposed_domains` (JSONB — list of {sequence_order, domain_name, domain_description, weight_pct}), `source_notes` (text — agent's explanation of where data was found and confidence level), `agent_run_id` (FK → agent_runs), `status` (`pending_review` | `approved` | `rejected`), `reviewed_by_admin_id` (nullable FK → admin_users), `reviewed_at` (nullable timestamp), `rejection_notes` (nullable text), `created_at`

### `practitioner_certification_goals`
A practitioner's history with a certification — recommended, chosen, in progress, or achieved. One practitioner can have several over a career; this is why it's a table and not a column on `practitioners`.
- `id`, `practitioner_id` (FK), `certification_id` (FK), `status` (`recommended` | `selected` | `in_progress` | `achieved` | `abandoned`), `recommended_at`, `selected_at` (nullable), `achieved_at` (nullable)

### `certification_advisor_responses`
The raw answers to the targeted questionnaire (Step 2.3), kept rather than discarded after the recommendation is made — useful both for re-running the advisor later as the catalog grows, and for reviewing whether the questions themselves are working.
- `id`, `practitioner_id` (FK), `responses` (jsonb), `created_at`

### `skill_profile_events` (append-only)
Raw evidence of what a practitioner knows, from any source.
- `id`, `practitioner_id` (FK), `skill_id` (FK), `source` (`certification` | `self_assessment` | `quiz_attempt` | `project_history`), `signal_strength` (0–1), `occurred_at`, `metadata` (jsonb — e.g. which cert, which attempt id)

### `skill_profile_snapshots` (derived)
Current best estimate per practitioner × skill. Rebuilt by the Skill Profiler Agent from quiz-attempt events only (Phase 9.4). Drives the Skill Radar, which shows the ~10–15 top-level overarching skills (root nodes in the skill graph where `parent_skill_id IS NULL`). Never hand-edited.
- `practitioner_id` (FK), `skill_id` (FK), `mastery_score` (0–1), `confidence` (0–1), `last_computed_at` — PK on (`practitioner_id`, `skill_id`)

### `certification_domain_scores` (derived)
Per-practitioner, per-domain mastery scores. Computed exclusively from quiz attempts for items where `is_cert_evaluated = true` (Phase 10.4). Drives the certification domain gap bar chart — a separate, exam-specific view from the broad skill radar.

- `id`, `practitioner_id` (FK), `certification_domain_id` (FK → certification_domains), `mastery_score` (float 0–1), `confidence` (float 0–1), `source` (`self_assessment_estimate` | `quiz_derived`), `last_computed_at` — Unique constraint on (`practitioner_id`, `certification_domain_id`).

**Source semantics:** When a profile is first locked, the Domain Scorer Agent writes `self_assessment_estimate` rows as a starting baseline (derived from the self-assessment ratings via LLM reasoning — max confidence 0.5). Once a practitioner submits cert-evaluated quiz answers for a domain, those rows are updated with `source = 'quiz_derived'` and take precedence. A `quiz_derived` row is never overwritten by a `self_assessment_estimate`.

### `mastery_history` (append-only, time-series)
A historical record appended by the Skill Profiler every time it upserts `skill_profile_snapshots`. Used to drive the Progress Trend Chart on the practitioner's Adoption Trends tab.
- `id`, `practitioner_id` (FK), `skill_id` (FK), `mastery_score` (float 0–1), `recorded_at` (timestamp)
- No unique constraint — multiple rows per (practitioner, skill) are expected and intentional. Rows older than 90 days are pruned by a background maintenance task to bound table growth.

### `learning_paths` / `learning_path_items`
The Curriculum Planner's output.
- `learning_paths`: `id`, `practitioner_id` (FK), `generated_at`, `status` (`draft` | `active` | `completed`)
- `learning_path_items`: `id`, `learning_path_id` (FK), `skill_id` (FK), `sequence_order`, `resource_type` (`item_set` | `scenario_lab` | `external_reading`), `status` (`pending` | `in_progress` | `done`)

### `items`
The question/scenario bank the Item-Writer agent populates.
- `id`, `skill_id` (FK), `item_type` (`mcq` | `free_text` | `scenario`), `prompt`, `answer_key` (jsonb), `trap_explanation` (nullable text — the reveal copy for the trap mechanic), `difficulty` (numeric), `calibration_stats` (jsonb — running accuracy, used to recalibrate difficulty over time), `generation` (integer, default 1 — the round this item belongs to; see Step 9.5), `certification_domain_id` (nullable FK → `certification_domains` — which exam domain this item tests; NULL for legacy or non-cert items), `is_cert_evaluated` (boolean, default false — `true` if this topic is directly assessed in the certification exam, `false` for supplementary/context items that support understanding but aren't in the exam blueprint)

Items with `is_cert_evaluated = true` are the only ones that change a practitioner's `certification_domain_scores`. Items with `is_cert_evaluated = false` still affect the broad Skill Radar via `skill_profile_snapshots`, but do not improve exam-domain readiness scores.

### `attempts`
- `id`, `practitioner_id` (FK), `item_id` (FK), `response` (jsonb), `score` (numeric), `grader_rationale` (text), `is_trap_selected` (nullable boolean), `attempted_at`

### `usage_events` (append-only)
Adoption Pulse's raw signal — normalized regardless of source.
- `id`, `practitioner_id` (FK), `signal_type` (`claude_code_session` | `git_commit` | `other`), `skill_id` (nullable FK — inferred mapping), `raw_ref` (pointer back to source record, not the raw payload), `occurred_at`, `ingested_at`

### `correlation_snapshots` (derived)
The Correlation Agent's output: trained vs. adopted, per practitioner × skill.
- `id`, `practitioner_id` (FK), `skill_id` (FK), `trained_score` (from `skill_profile_snapshots`), `adoption_score` (derived from `usage_events` recency/density), `gap_score`, `computed_at`

### `nudge_categories`
Categories for admin-initiated nudge campaigns (Phase 7). Each row is either a suggestion generated by the Nudge Category Generator Agent from aggregate KPI data, or a custom description typed by an admin.
- `id`, `description` (text — human-readable label, e.g. "Practitioners who haven't taken quizzes in 7 days"), `criteria` (jsonb — machine-readable filter params, e.g. `{"no_quiz_days_gte": 7}`), `is_custom` (boolean — `true` when the admin typed it manually), `created_by_admin_id` (FK → `admin_users`), `created_at`

Supported `criteria` keys (resolved by the Python `resolve_recipients()` function, not by the LLM):
- `no_quiz_days_gte: N` — no attempts in last N days
- `no_profile: true` — no active profile
- `profile_unrated: true` — active profile but no skill assessments saved
- `mastery_stalled_days_gte: N` — no mastery improvement in last N days
- `skill_gap_skill_id: UUID` — gap_score ≥ 0.5 on this skill
- `near_cert_ready: true` — cert-relevant mastery avg ≥ 80 %
- `custom_description: str` — free text; resolver returns all practitioners for manual review

### `nudges`
- `id`, `practitioner_id` (FK), `nudge_category_id` (nullable FK → `nudge_categories` — set for admin campaigns, null for nightly-pulse nudges), `nudge_type` (`gap_alert` | `encouragement` | `reminder` | `campaign`), `channel` (`email` | `in_app`), `subject` (nullable text — email subject line), `content` (text), `status` (`drafted` | `approved` | `sent`), `is_read` (boolean, default false), `read_at` (nullable timestamp — set when the practitioner opens the nudge in the UI), `created_by_admin_id` (nullable FK → `admin_users` — set for admin-initiated campaigns, null for nightly-pulse nudges), `created_at`, `sent_at` (nullable)

Nightly-pulse nudges start at `drafted` (awaiting approval). Admin-campaign nudges go directly to `sent` when the admin clicks Send. See `docs/human-in-the-loop.md` for ownership of tone and content.

### `rollups`
Leadership-facing aggregates. Never keyed to an individual.
- `id`, `scope` (`team` | `practice`), `scope_ref`, `period_start`, `period_end`, `metrics` (jsonb), `narrative` (text), `min_cohort_size_met` (boolean), `created_at`

### `agent_runs`
Every agent invocation, full stop.
- `id`, `agent_name`, `workflow_run_id` (nullable FK), `input` (jsonb), `output` (jsonb), `model_used`, `tokens_input`, `tokens_output`, `latency_ms`, `status` (`success` | `error`), `error_message` (nullable), `started_at`, `completed_at`

### `workflow_runs`
- `id`, `workflow_name` (`recommend_certification` | `generate_learning_path` | `nightly_pulse` | `nudge_campaign`), `triggered_by`, `status` (`running` | `completed` | `failed`), `started_at`, `completed_at`

## Relationships at a glance

```
certification_providers ─< certifications ─< certification_skills >─ skills
                                          └─< certification_domain_versions ─< certification_domains
                                          └─< certification_domain_proposals (pending admin review)

practitioners ─┬─< certification_advisor_responses
               ├─< practitioner_certification_goals >─ certifications
               ├─< practitioner_profiles ─┬─ certification_id → certifications (NOT NULL, Phase 10.1)
               │                          └─ domain_version_id → certification_domain_versions (set at lock time, Phase 10.5)
               ├─< profile_skill_assessments >─ skills (per-profile ratings, preserved but not used for radar)
               ├─< skill_profile_events >─ skills
               ├─< skill_profile_snapshots >─ skills     (broad radar — all quiz signals)
               ├─< certification_domain_scores >─ certification_domains  (gap chart — cert-eval only)
               ├─< mastery_history >─ skills              (append-only time-series)
               ├─< learning_paths >─< learning_path_items >─ skills
               ├─< attempts >─ items ─┬─ skills
               │                      └─ certification_domains (nullable — tagged in Phase 10.6)
               ├─< usage_events >─ skills (nullable)
               ├─< correlation_snapshots >─ skills
               └─< nudges >─ nudge_categories (nullable)

admin_users ─< sessions
admin_users ─< nudge_categories
admin_users ─< nudges (created_by_admin_id, nullable)
admin_users ─< certification_domain_versions (created_by_admin_id, nullable)
admin_users ─< certification_domain_proposals (reviewed_by_admin_id, nullable)
practitioners ─< sessions   (sessions is polymorphic via identity_type)

workflow_runs ─< agent_runs
agent_runs ─< certification_domain_versions (agent_run_id, nullable — set for agent-driven refreshes)
agent_runs ─< certification_domain_proposals (agent_run_id)
rollups            (aggregated — no direct practitioner FK by design; removed Phase 9.1)
```

### Two-tier scoring model (Phase 10)

| Signal | Radar (`skill_profile_snapshots`) | Domain gap chart (`certification_domain_scores`) |
|---|---|---|
| Cert-evaluated quiz answer (`is_cert_evaluated = true`) | ✓ moves mastery score | ✓ moves domain readiness score |
| Supplementary quiz answer (`is_cert_evaluated = false`) | ✓ moves mastery score | — no effect |
| Self-assessment ratings (profile lock) | — not used (Phase 9.4) | Initial estimate only (`self_assessment_estimate`, max confidence 0.5; `quiz_derived` takes precedence) |

The radar shows the broad learning picture across ~10–15 overarching skills. The domain gap chart shows exam-specific readiness that matters for passing the actual certification.

## Seed catalog (Step 2.2)

A starting set, verified against current sources rather than assumed — spans four providers on purpose, so the advisor logic in Step 2.3 has real variety to reason over rather than a single-provider list that only looks agnostic.

**Anthropic** (Claude Partner Network — registration needs a partner-org email; note this in `eligibility_notes`):
| Code | Name | Level | Coding required? |
|---|---|---|---|
| `CCAO-F` | Claude Certified Associate – Foundations | foundational | No — explicitly not aimed at developers or agentic builders |
| `CCDV-F` | Claude Certified Developer – Foundations | foundational | Yes |
| `CCAF` | Claude Certified Architect – Foundations | foundational | Technical background recommended |
| `CCAR-P` | Claude Certified Architect – Professional | professional | Yes |

**AWS** (illustrative): `AIF-C01` AWS Certified AI Practitioner (foundational, no coding) · AWS Certified Machine Learning Engineer – Associate (associate, coding required).
**Google Cloud** (illustrative): Generative AI Leader (foundational, no coding) · Professional Machine Learning Engineer (professional, coding required).
**Microsoft** (illustrative): Azure AI Fundamentals — AI-900 (foundational, no coding) · Azure AI Engineer Associate — AI-102 (associate, coding required).

The AWS/Google/Microsoft rows are a credible starting point, not a guarantee of what's live by the time you read this — this market moved fast enough in the months before this doc was written (AWS retired its ML Specialty exam and split it into an Associate-level engineering track and a separate Generative AI Developer track in the same window) that treating any fixed list as permanent would be a mistake. That's what `last_verified_at` is for: re-check a row before recommending it if that date is more than a few months old, rather than trusting the seed data forever.

## Auth tables (Step 5.2)

Two roles. Two login paths. One session table.

### `admin_users`
Leadership and admin accounts. Entirely separate from `practitioners` — these roles see individual and aggregate data; they do not take quizzes or receive learning paths.
- `id`, `name`, `email` (unique), `role` (`admin` | `leadership`), `password_hash` (bcrypt, one-way — never reversible), `must_change_password` (boolean, default `true` — set to `false` only after a successful password change), `created_at`, `last_login_at` (nullable)

Every new admin account ships with password `"welcome"` and `must_change_password = true`. The first successful login goes to a forced change-password screen before the user reaches any data. Passwords can be changed at any time from the account settings page.

### `sessions`
Server-side sessions for both role types. The session token (a UUID) lives only in an HTTP-only cookie — never in `localStorage` or `sessionStorage`.
- `id` (uuid — the opaque cookie value), `identity_type` (`practitioner` | `admin`), `practitioner_id` (nullable FK → `practitioners` — populated when `identity_type = practitioner`), `admin_user_id` (nullable FK → `admin_users` — populated when `identity_type = admin`), `created_at`, `last_seen_at`

Practitioner sessions are long-lived (no hard expiry — every request updates `last_seen_at`). Admin sessions expire after inactivity (a reasonable timeout, e.g. 8 hours, configured in `settings`).

## What's deliberately not here yet

Any table for storing raw usage-log payloads (we store pointers via `raw_ref`, not the payloads themselves — keep sensitive logs where they already live), and anything for the frontend to cache client-side (React state only, per `docs/coding-guidelines.md`).
