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

### `skill_profile_events` (append-only)
Raw evidence of what a practitioner knows, from any source.
- `id`, `practitioner_id` (FK), `skill_id` (FK), `source` (`certification` | `self_assessment` | `quiz_attempt` | `project_history`), `signal_strength` (0–1), `occurred_at`, `metadata` (jsonb — e.g. which cert, which attempt id)

### `skill_profile_snapshots` (derived)
Current best estimate per practitioner × skill. Rebuilt by the Skill Profiler Agent, never hand-edited.
- `practitioner_id` (FK), `skill_id` (FK), `mastery_score` (0–1), `confidence` (0–1), `last_computed_at` — PK on (`practitioner_id`, `skill_id`)

### `learning_paths` / `learning_path_items`
The Curriculum Planner's output.
- `learning_paths`: `id`, `practitioner_id` (FK), `generated_at`, `status` (`draft` | `active` | `completed`)
- `learning_path_items`: `id`, `learning_path_id` (FK), `skill_id` (FK), `sequence_order`, `resource_type` (`item_set` | `scenario_lab` | `external_reading`), `status` (`pending` | `in_progress` | `done`)

### `items`
The question/scenario bank the Item-Writer agent populates.
- `id`, `skill_id` (FK), `item_type` (`mcq` | `free_text` | `scenario`), `prompt`, `answer_key` (jsonb), `trap_explanation` (nullable text — the reveal copy for the trap mechanic), `difficulty` (numeric), `calibration_stats` (jsonb — running accuracy, used to recalibrate difficulty over time)

### `attempts`
- `id`, `practitioner_id` (FK), `item_id` (FK), `response` (jsonb), `score` (numeric), `grader_rationale` (text), `is_trap_selected` (nullable boolean), `attempted_at`

### `usage_events` (append-only)
Adoption Pulse's raw signal — normalized regardless of source.
- `id`, `practitioner_id` (FK), `signal_type` (`claude_code_session` | `git_commit` | `other`), `skill_id` (nullable FK — inferred mapping), `raw_ref` (pointer back to source record, not the raw payload), `occurred_at`, `ingested_at`

### `correlation_snapshots` (derived)
The Correlation Agent's output: trained vs. adopted, per practitioner × skill.
- `id`, `practitioner_id` (FK), `skill_id` (FK), `trained_score` (from `skill_profile_snapshots`), `adoption_score` (derived from `usage_events` recency/density), `gap_score`, `computed_at`

### `nudges`
- `id`, `practitioner_id` (FK), `nudge_type` (`gap_alert` | `encouragement` | `reminder`), `channel` (`email` | `in_app`), `content` (text), `status` (`drafted` | `approved` | `sent`), `created_at`, `sent_at` (nullable)

Nothing auto-sends. `status` starts at `drafted`; see `docs/human-in-the-loop.md`.

### `rollups`
Leadership-facing aggregates. Never keyed to an individual.
- `id`, `scope` (`team` | `practice`), `scope_ref`, `period_start`, `period_end`, `metrics` (jsonb), `narrative` (text), `min_cohort_size_met` (boolean), `created_at`

### `agent_runs`
Every agent invocation, full stop.
- `id`, `agent_name`, `workflow_run_id` (nullable FK), `input` (jsonb), `output` (jsonb), `model_used`, `tokens_input`, `tokens_output`, `latency_ms`, `status` (`success` | `error`), `error_message` (nullable), `started_at`, `completed_at`

### `workflow_runs`
- `id`, `workflow_name` (`generate_learning_path` | `nightly_pulse`), `triggered_by`, `status` (`running` | `completed` | `failed`), `started_at`, `completed_at`

## Relationships at a glance

```
practitioners ─┬─< skill_profile_events >─ skills
               ├─< skill_profile_snapshots >─ skills
               ├─< learning_paths >─< learning_path_items >─ skills
               ├─< attempts >─ items ─ skills
               ├─< usage_events >─ skills (nullable)
               ├─< correlation_snapshots >─ skills
               └─< nudges

workflow_runs ─< agent_runs
rollups            (aggregated — no direct practitioner FK by design)
```

## What's deliberately not here yet

Auth/user-role tables (Step 5.2), any table for storing raw usage-log payloads (we store pointers via `raw_ref`, not the payloads themselves — keep sensitive logs where they already live), and anything for the frontend to cache client-side (React state only, per `docs/coding-guidelines.md`).
