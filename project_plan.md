# Mastery Pulse — Project Plan

## How to use this document

1. **One step at a time.** Paste that step's full section (Goal through Definition of Done) into a fresh Claude Code session as the task.
2. **Check "Context to load" first.** Tell Claude Code to read those docs before it starts. `CLAUDE.md` already points it at the repo layout, so it can usually find its own way, but naming the doc up front saves a round trip.
3. **The Definition of Done is the actual gate** — not "the code looks plausible." Don't move to the next step until it's met.
4. **Run `/clear` after every step.** Steps are written to be self-contained on purpose: each one only assumes what the *previous* step's Definition of Done already guarantees exists. That's what makes clearing safe.
5. **Steps marked 👤 need you**, not just Claude Code — usually the prompt, a rubric, or a policy decision, not the surrounding Python. Full rationale for all nine in `docs/human-in-the-loop.md`; each flagged step below repeats the short version inline.

Testing philosophy lives in `docs/coding-guidelines.md` — short version: every scenario is Given/When/Then, agents are tested against a stub Claude client (not the live API, so tests are fast, free, and deterministic), and "done" means this step's scenarios are green.

## Step index

**Phase 0 — Foundations**
- [x] 0.1 Repo scaffolding & tooling
- [x] 0.2 Database schema v1 + migrations
- [x] 0.3 Synthetic seed data generator
- [x] 0.4 Agent framework 👤

**Phase 1 — MCP Adapters**
- [x] 1.1 `mcp-learning-portal` MCP server
- [x] 1.2 `mcp-usage-signals` MCP server 👤

**Phase 2 — Mastery Mesh (learning loop)**
- [x] 2.1 Skill graph & practitioner profile API
- [x] 2.2 Certification catalog + seed data
- [x] 2.3 Certification Advisor Agent 👤
- [x] 2.4 Skill Profiler Agent
- [x] 2.5 Curriculum Planner Agent
- [x] 2.6 Item-Writer Agent 👤
- [x] 2.7 Grader Agent 👤
- [x] 2.8 Learning-path orchestrator workflow + API

**Phase 3 — Adoption Pulse (signal loop)**
- [x] 3.1 Usage-Signal Agent
- [x] 3.2 Correlation Agent 👤
- [x] 3.3 Nudge Composer Agent 👤
- [x] 3.4 Rollup Reporter Agent 👤
- [x] 3.5 Nightly Pulse orchestrator workflow
- [x] 3.6 API routes for the pulse loop

**Phase 4 — Frontend**
- [x] 4.1 App shell, routing, typed API client
- [x] 4.2 Certification Advisor questionnaire UI
- [x] 4.3 Skill Radar dashboard
- [x] 4.4 Quiz Runner (trap-reveal) 👤
- [x] 4.5 Adoption trend dashboard
- [x] 4.6 Leadership rollup view
- [x] 4.7 Full-journey Playwright suite

**Phase 5 — Hardening & Packaging**
- [x] 5.1 Observability
- [x] 5.2 Auth & access control 👤
- [x] 5.3 Deployment packaging
- [x] 5.4 Full regression pass + demo script
- [x] 5.5 Bug fixes (pre-Phase 6 cleanup)

**Phase 6 — Practitioner Profile Redesign**
- [x] 6.1 Practitioner profile data model & API
- [x] 6.2 Enhanced questionnaire 👤
- [x] 6.3 "Build my profile" landing page
- [x] 6.4 Profile questionnaire + certification selection wizard
- [x] 6.5 Profile-linked skill assessment
- [x] 6.6 Profile management & activation
- [x] 6.7 Skill Radar enhancements
- [x] 6.8 Quiz profile-awareness & navigation fix

---

# Phase 0 — Foundations

### Step 0.1 — Repo scaffolding & tooling

**Goal:** the skeleton every later step builds into.
**Preconditions:** none.
**Context to load:** `docs/architecture.md` (Folder structure section).
**Build:**
- Folder structure exactly as laid out in `docs/architecture.md`.
- `backend/pyproject.toml` — FastAPI, SQLAlchemy, Alembic, Pydantic v2, ruff, black, pytest, pytest-asyncio, httpx.
- `frontend/package.json` — Vite + React + TypeScript, TanStack Query, Playwright.
- `.env.example`, `.gitignore` (`node_modules`, `.venv`, `__pycache__`, `.env`), a `README.md` stub pointing at `CLAUDE.md` and this file.

**Precondition:** PostgreSQL 14+ installed locally; `mastery_pulse` and `mastery_pulse_test` databases created (see `README.md`).

**Scenario tests:** none yet — this step is scaffolding, not behavior.
**Definition of done:** `cd backend && pytest` runs cleanly with zero tests; `cd frontend && npm run build` succeeds on the default template.

---

### Step 0.2 — Database schema v1 + migrations

**Goal:** the first migration, covering only what Phase 0–2 need: `practitioners`, `skills`, `skill_profile_events`, `skill_profile_snapshots`, `agent_runs`, `workflow_runs`. The rest of `docs/data-model.md` comes in later, smaller migrations — easier to reason about and to reverse.
**Preconditions:** 0.1.
**Context to load:** `docs/data-model.md` (full).
**Build:** SQLAlchemy models for the six tables above; one Alembic migration.

**Scenario tests:**
- *Running migrations twice is safe* — Given a fresh database, when `alembic upgrade head` runs twice in a row, then the second run makes no changes and exits cleanly.
- *Downgrade reverses cleanly* — Given the migration has been applied, when `alembic downgrade base` runs, then none of this migration's tables remain.

**Definition of done:** both scenarios pass; `alembic upgrade head` runs clean against the local `mastery_pulse` database.

---

### Step 0.3 — Synthetic seed data generator

**Goal:** realistic fake data. There's no real client data yet, and every later scenario test and demo needs something believable to run against.
**Preconditions:** 0.2.
**Context to load:** `docs/data-model.md`.
**Build:** `backend/seed/generate.py` using Faker — ~20 practitioners, a skill graph of ~15–20 skills across 3–4 categories, a spread of `skill_profile_events` across all four sources.

**Scenario tests:**
- *Seeding is idempotent* — Given an already-seeded database, when the seed script runs again, then the practitioner count doesn't double (decide clear-then-seed vs. upsert, then encode that choice in the test).
- *Seeded data spans all signal sources* — Given a freshly seeded database, when querying `skill_profile_events` by source, then `certification`, `self_assessment`, `quiz_attempt`, and `project_history` are all represented.

**Definition of done:** both pass; `python -m seed.generate` populates a fresh DB in under 10 seconds.

---

### Step 0.4 — Agent framework 👤

**Goal:** the base `Agent` class every one of the other nine agents extends — Claude client wrapper, Structured Outputs handling, `agent_runs` persistence, retry/error behavior.
**Preconditions:** 0.2 (needs `agent_runs`).
**Context to load:** `docs/architecture.md` (Agent contract + Structured output sections), `docs/coding-guidelines.md`, `docs/human-in-the-loop.md`.
**Build:** `backend/app/agents/base.py` (the generic `Agent[TInput, TOutput]` class), the `agents/prompts/` convention, a stub Claude client interface for testing.

**Scenario tests:**
- *A successful call persists a complete `agent_runs` row* — Given a trivial test agent with a fixed stub response, when it runs, then an `agent_runs` row exists with status `success`, non-null tokens and latency, and output matching the schema.
- *A malformed stub response is caught, not silently accepted* — Given a stub response that violates the agent's output schema, when the agent runs, then it reports a validation error and `agent_runs` records status `error` with a message.
- *An agent with no MCP dependency never touches the MCP client machinery* — Given an agent with no MCP server configured, when it runs, then no MCP subprocess is spawned.

**Definition of done:** all three pass.

> 👤 **Human-in-the-loop:** review this file yourself before building on it — every other agent inherits this contract, so a wrong call here is a wrong call nine times over. See `docs/human-in-the-loop.md`.

---

# Phase 1 — MCP Adapters

### Step 1.1 — `mcp-learning-portal` MCP server

**Goal:** a local (stdio) MCP server exposing `get_certifications`, `get_course_completions`, `get_self_assessment` over exports dropped in a local folder.
**Preconditions:** 0.1 (reads flat files, not the DB — independent of the schema steps).
**Context to load:** `docs/architecture.md` (MCP strategy section).
**Build:** `backend/app/mcp_servers/learning_portal/server.py` using the official `mcp` Python package; fixture exports under `backend/tests/fixtures/learning_portal/`.

**Scenario tests:**
- *`get_certifications` returns a known practitioner's certification* — Given a fixture export containing a certification for a named practitioner, when the tool is called for them, then the response includes it with its covered skills.
- *A practitioner with no data returns an empty list, not an error* — Given no records for an unknown practitioner, when any of the three tools is called, then it returns an empty list.

**Definition of done:** both pass called through a real `ClientSession` / `stdio_client` round trip — not just by calling the underlying Python function directly. Proving the MCP wiring works end-to-end is the actual point of this step.

---

### Step 1.2 — `mcp-usage-signals` MCP server 👤

**Goal:** a local MCP server exposing `get_claude_code_sessions` and `get_commit_activity`.
**Preconditions:** 0.1.
**Context to load:** `docs/architecture.md`, `docs/human-in-the-loop.md`.
**Build:** `backend/app/mcp_servers/usage_signals/server.py`. Before writing the tool logic: 👤 decide and document (in the module docstring) which repos/tools count as signal and how a session or commit maps to a `skill_id`.

**Scenario tests:**
- *A mapped session produces the right skill mapping* — Given a fixture session log referencing clear skill-relevant work, when `get_claude_code_sessions` is called, then the returned session includes an inferred mapping to that skill.
- *An ambiguous session is returned unmapped, not guessed* — Given a fixture session with no clear signal, when called, then the session comes back with a null skill mapping rather than a low-confidence guess.

**Definition of done:** both pass; the mapping rule is written down, not just implicit in code.

> 👤 **Human-in-the-loop:** design the mapping rule yourself. Get it wrong and Adoption Pulse either misses real adoption or flags noise as signal — no amount of clean code fixes a bad modeling decision. See `docs/human-in-the-loop.md`.

---

# Phase 2 — Mastery Mesh (learning loop)

### Step 2.1 — Skill graph & practitioner profile API

**Goal:** CRUD for practitioners and the skill graph — the foundation every agent below reads from.
**Preconditions:** 0.2, 0.3.
**Context to load:** `docs/data-model.md`.
**Build:** `backend/app/api/routes/practitioners.py`, `skills.py`; Pydantic schemas.

**Scenario tests:**
- *Creating then fetching a practitioner returns matching data.*
- *Fetching a nonexistent practitioner returns 404, not a 500.*
- *The skill graph endpoint preserves hierarchy* — Given seeded skills with parent/child relationships, when `GET /skills` is called, then child skills correctly reference their `parent_skill_id`.

**Definition of done:** all three pass.

---

### Step 2.2 — Certification catalog + seed data

**Goal:** the provider-agnostic certification catalog — the thing that makes the advisor in the next step possible at all.
**Preconditions:** 2.1 (certifications map onto the skill graph).
**Context to load:** `docs/data-model.md` (Seed catalog section).
**Build:** `certification_providers`, `certifications`, `certification_skills` tables/migration; seed script populating the four verified Anthropic certifications (CCAO-F, CCDV-F, CCAF, CCAR-P) plus illustrative AWS, Google Cloud, and Microsoft entries — see the seed list in `docs/data-model.md` rather than re-deriving it here.

**Scenario tests:**
- *The seeded catalog spans more than one provider* — Given a freshly seeded database, when querying `certifications` joined to `certification_providers`, then at least four distinct providers are represented.
- *Every certification maps to at least one skill* — Given the seeded catalog, when checking `certification_skills`, then no certification is orphaned with zero mapped skills (an advisor recommendation with nothing to build a learning path from is a dead end).

**Definition of done:** both pass; re-run `docs/data-model.md`'s seed list against current sources if `last_verified_at` on any row is more than a few months old by the time you build this.

---

### Step 2.3 — Certification Advisor Agent 👤

**Goal:** the actual front door — a short questionnaire that recommends a best-fit certification from the catalog, regardless of provider.
**Preconditions:** 2.2.
**Context to load:** `docs/architecture.md` (Certification Advisor section), `docs/human-in-the-loop.md`.
**Build:** `backend/app/agents/certification_advisor.py` + `prompts/certification_advisor.md`, and an API route that accepts questionnaire answers and returns a recommendation. 👤 The four questions in `docs/architecture.md` are a starting point — finalize the wording and the recommendation weighting yourself.

**Scenario tests:**
- *A non-coder interested in Anthropic gets pointed at Associate, not Architect or Developer* — Given answers indicating no coding background, a business/advising focus, and an Anthropic preference, when the agent runs, then the recommendation is `CCAO-F`, not one of the coding-required tracks.
- *An experienced architect with no provider preference gets a rationale that names the trade-off, not just a pick* — Given answers indicating strong technical experience, an architecting focus, and no provider preference, when the agent runs, then the response includes a primary recommendation and a short rationale referencing at least one alternative.
- *Answers are persisted even when the recommendation is later ignored* — Given a completed questionnaire, when the agent runs, then a `certification_advisor_responses` row and a `practitioner_certification_goals` row (status `recommended`) both exist, independent of whether the practitioner ever acts on it.

**Definition of done:** all three pass against the stub Claude client.

> 👤 **Human-in-the-loop:** the question set and the recommendation logic are yours to own — see `docs/human-in-the-loop.md`.

---

### Step 2.4 — Skill Profiler Agent

**Goal:** turn `skill_profile_events` (plus live data from `mcp-learning-portal`) into `skill_profile_snapshots`.
**Preconditions:** 0.4, 2.1, 1.1.
**Context to load:** `docs/architecture.md` (agent table + contract), `docs/data-model.md`.
**Build:** `backend/app/agents/skill_profiler.py` + `prompts/skill_profiler.md`.

**Scenario tests:**
- *New practitioner with a completed certification gets an initial profile* — Given no existing snapshot and one certification signal, when the agent runs, then a snapshot is created with `mastery_score > 0`.
- *Conflicting signals are weighted, not overwritten by the latest one* — Given a low quiz score and a relevant certification for the same skill, when the agent runs, then the resulting score reflects both, not just one.
- *Re-running is idempotent absent new signals* — Given a practitioner already profiled with no new events since, when the agent runs again, then the snapshot is unchanged.

**Definition of done:** all three pass against the stub Claude client.

---

### Step 2.5 — Curriculum Planner Agent

**Goal:** turn a skill profile into a learning path — weighted toward the practitioner's active certification goal when one exists, and toward general skill gaps when it doesn't.
**Preconditions:** 2.4 (required); 2.3 (optional — enables certification-goal-aware prioritization if a goal has been selected).
**Context to load:** `docs/architecture.md`, `docs/data-model.md`.
**Build:** `backend/app/agents/curriculum_planner.py` + prompt.

**Scenario tests:**
- *A practitioner with one weak skill gets a path prioritizing it* — the resulting `learning_path_items` sequence places that skill first.
- *A practitioner with an active certification goal gets a path weighted toward that certification's skills* — Given a `practitioner_certification_goals` row with status `selected` and that certification's `certification_skills` weights, when the agent runs, then the path prioritizes those skills over equally-weak skills outside the certification's scope.
- *A fully-mastered practitioner gets an empty or maintenance-only path, not an error.*

**Definition of done:** all three pass.

---

### Step 2.6 — Item-Writer Agent 👤

**Goal:** generate and calibrate practice items, including the trap-reveal mechanic.
**Preconditions:** 2.1.
**Context to load:** `docs/architecture.md`, `docs/human-in-the-loop.md`.
**Build:** `backend/app/agents/item_writer.py` + `prompts/item_writer.md` — 👤 write this prompt yourself: what makes a good trap, and what the reveal copy says.

**Scenario tests:**
- *A generated MCQ item has exactly one correct option and a non-empty trap explanation.*
- *Recalibration responds to a low accuracy rate* — Given an item whose `calibration_stats` show near-zero accuracy across attempts, when recalibration runs, then its difficulty rating changes accordingly.

**Definition of done:** both pass.

> 👤 **Human-in-the-loop:** this is your signature pedagogical device from the CCAF materials, and the single most "you" part of this product. Write the prompt yourself; review generated items against your own judgment before trusting this agent at scale. See `docs/human-in-the-loop.md`.

---

### Step 2.7 — Grader Agent 👤

**Goal:** score attempts, including free text, with a rationale.
**Preconditions:** 2.6.
**Context to load:** `docs/architecture.md`, `docs/human-in-the-loop.md`.
**Build:** `backend/app/agents/grader.py` + `prompts/grader.md` — 👤 write the rubric, especially partial-credit rules for free text.

**Scenario tests:**
- *A fully correct MCQ response scores full marks* — `score == 1.0`, `is_trap_selected` false.
- *A trap-option response is flagged and explained* — `is_trap_selected` true, `grader_rationale` references the misconception.
- *A partially correct free-text response gets partial credit with a rationale* — `0 < score < 1`, rationale explains what was missing.

**Definition of done:** all three pass.

> 👤 **Human-in-the-loop:** the rubric encodes what you actually value in an answer. Get it wrong and every downstream skill score quietly measures the wrong thing. See `docs/human-in-the-loop.md`.

---

### Step 2.8 — Learning-path orchestrator workflow + API

**Goal:** wire 2.4 → 2.5 → 2.6 into the `generate_learning_path` workflow; expose it and attempt submission over the API. This is the first true end-to-end milestone — treat it as proof that Mastery Mesh's core loop works.
**Preconditions:** 2.4, 2.5, 2.6, 2.7.
**Context to load:** `docs/architecture.md` (Orchestration section).
**Build:** `backend/app/workflows/generate_learning_path.py`; routes for requesting a path and submitting an attempt.

**Scenario tests:**
- *Requesting a path runs all three agents in order* — a `workflow_runs` row with status `completed` and three linked `agent_runs` rows in the expected order.
- *A failure partway through is recorded, not swallowed* — Given the Item-Writer step is forced to fail, when the workflow runs, then `workflow_runs.status` is `failed` and the response surfaces it, not a silent 200.
- *Submitting an attempt end-to-end updates the snapshot on the next profiler run.*

**Definition of done:** all three pass.

> **Design note — Skill Radar refresh cadence:** Submitting a quiz attempt writes a `skill_profile_event` of type `quiz_attempt`. The Skill Radar is *not* automatically re-profiled after each attempt — that would trigger an LLM call on every answer, which is unnecessary and expensive. Instead, practitioners complete their quizzes and then click "Regenerate learning path" to re-run the full Skill Profiler → Curriculum Planner → Item-Writer pipeline, updating the radar with all accumulated evidence at once. This is deliberate; do not add background re-profiling without explicit approval.

---

# Phase 3 — Adoption Pulse (signal loop)

### Step 3.1 — Usage-Signal Agent

**Goal:** ingest usage evidence via `mcp-usage-signals` and write normalized `usage_events`.
**Preconditions:** 0.4, 1.2, 2.1.
**Context to load:** `docs/architecture.md`, `docs/data-model.md`.
**Build:** `backend/app/agents/usage_signal.py` + prompt.

**Scenario tests:**
- *A mapped session produces a `usage_event` linked to the right skill.*
- *An unmapped session still produces a record, just without a `skill_id`* — evidence isn't discarded for being ambiguous.

**Definition of done:** both pass.

---

### Step 3.2 — Correlation Agent 👤

**Goal:** compute trained-vs-adopted gap scores.
**Preconditions:** 2.4, 3.1.
**Context to load:** `docs/architecture.md`, `docs/human-in-the-loop.md`.
**Build:** `backend/app/agents/correlation.py` + `prompts/correlation.md` — 👤 design the methodology and the correlation-not-causation framing into the prompt itself, not just a code comment.

**Scenario tests:**
- *High mastery with no recent usage produces a visible gap* — Given a high snapshot score and no `usage_events` in 30+ days for that skill, then `gap_score` is materially above zero.
- *High mastery with regular usage produces a near-zero gap* — same score, recent frequent usage, `gap_score` near zero.
- *Low mastery is not reported as an adoption gap* — a low snapshot score, regardless of usage, is distinguished from case 1 rather than conflated with it (it's a training need, not an adoption problem).

**Definition of done:** all three pass.

> 👤 **Human-in-the-loop:** this is the most ethically load-bearing agent in the system — the one that decides someone looks like they're not using what they learned. Design it carefully rather than trusting a first-draft prompt. See `docs/human-in-the-loop.md`.

---

### Step 3.3 — Nudge Composer Agent 👤

**Goal:** draft individual nudges from correlation snapshots.
**Preconditions:** 3.2.
**Context to load:** `docs/architecture.md`, `docs/human-in-the-loop.md`.
**Build:** `backend/app/agents/nudge_composer.py` + `prompts/nudge_composer.md` — 👤 write and review the tone yourself.

**Scenario tests:**
- *A meaningful gap produces a drafted (not sent) nudge* — status `drafted`.
- *A near-zero gap produces no nudge at all* — don't nag people who are already fine.

**Definition of done:** both pass.

> 👤 **Human-in-the-loop:** nudges land in someone's inbox about themselves. A tone-deaf or demoralizing one does real damage to how this tool is received. Read every template before it can reach "approved." See `docs/human-in-the-loop.md`.

---

### Step 3.4 — Rollup Reporter Agent 👤

**Goal:** aggregate, privacy-safe leadership rollups.
**Preconditions:** 3.2.
**Context to load:** `docs/architecture.md`, `docs/data-model.md`, `docs/human-in-the-loop.md`.
**Build:** `backend/app/agents/rollup_reporter.py` + prompt — 👤 pick and hard-code the minimum cohort size.

**Scenario tests:**
- *A cohort at/above the minimum size produces a rollup with populated metrics* — `min_cohort_size_met` true.
- *A cohort below the minimum size is refused, not silently shown* — `min_cohort_size_met` false and metrics withheld (or the row isn't created — decide which, then test that).

**Definition of done:** both pass.

> 👤 **Human-in-the-loop:** this is a privacy decision with a number attached. Pick it deliberately; don't let a default slip in. See `docs/human-in-the-loop.md`.

---

### Step 3.5 — Nightly Pulse orchestrator workflow

**Goal:** wire 3.1 → 3.2 → 3.3 → 3.4 into the `nightly_pulse` workflow, routed through the Message Batches API (not latency-sensitive, and structured outputs are fully compatible with it at a 50% discount — see `docs/architecture.md`).
**Preconditions:** 3.1–3.4.
**Context to load:** `docs/architecture.md` (Model selection section).
**Build:** `backend/app/workflows/nightly_pulse.py`.

**Scenario tests:**
- *A full nightly run across multiple practitioners completes with one `workflow_runs` row* and all four steps executed per practitioner.
- *One practitioner's failure doesn't abort the whole run* — other practitioners still complete.

**Definition of done:** both pass.

---

### Step 3.6 — API routes for the pulse loop

**Goal:** expose correlation snapshots, nudges (for approval), and rollups.
**Preconditions:** 3.5.
**Context to load:** `docs/data-model.md`.
**Build:** routes for listing/approving nudges, fetching rollups by scope.

**Scenario tests:**
- *Approving a drafted nudge changes its status and sets `sent_at`.*
- *A rollup below the privacy floor is withheld by the API regardless of who's asking* — the floor holds at the API layer, not just at generation time.

**Definition of done:** both pass.

---

# Phase 4 — Frontend

### Step 4.1 — App shell, routing, typed API client

**Goal:** the skeleton everything else in Phase 4 builds into.
**Preconditions:** 2.1.
**Context to load:** `docs/architecture.md` (Folder structure), `/mnt/skills/public/frontend-design/SKILL.md`.
**Build:** Vite + React + TS app shell, route structure, a typed API client against the backend schemas.

**Scenario tests:** manual verification only — no user-facing behavior yet. Confirm the app builds and a smoke-test fetch to a running backend returns data.
**Definition of done:** `npm run build` succeeds; the smoke-test fetch works.

---

### Step 4.2 — Certification Advisor questionnaire UI

**Goal:** the actual entry screen — the four-question form and the recommendation result.
**Preconditions:** 4.1, 2.3.
**Build:** `components/CertAdvisor/`.

**Scenario tests (Playwright):**
- *Completing the questionnaire displays a primary recommendation with its rationale.*
- *A practitioner can accept a recommendation, moving its goal status from `recommended` to `selected`.*

**Definition of done:** both pass.

---

### Step 4.3 — Skill Radar dashboard

**Goal:** the individual skill-radar view.
**Preconditions:** 4.1, 2.4.
**Build:** `components/SkillRadar/`.

**Scenario tests (Playwright):**
- *A practitioner's radar renders one axis per skill matching their snapshot scores.*
- *A practitioner with no profile yet sees an empty state, not a broken chart.*

**Definition of done:** both pass.

---

### Step 4.4 — Quiz Runner (trap-reveal) 👤

**Goal:** the interactive quiz UI, including the trap-reveal moment.
**Preconditions:** 4.1, 2.6, 2.7.
**Context to load:** `docs/human-in-the-loop.md`.
**Build:** `components/QuizRunner/` — 👤 design the reveal interaction/animation yourself once the plumbing works.

**Scenario tests (Playwright):**
- *Selecting the trap option surfaces the reveal explanation panel.*
- *Selecting the correct option does not trigger the trap-reveal panel* — a normal correct-answer state shows instead.

**Definition of done:** both pass.

> 👤 **Human-in-the-loop:** the mechanic's effect on the practitioner lives as much in the UI beat as in the copy. Worth a personal design pass. See `docs/human-in-the-loop.md`.

---

### Step 4.5 — Adoption trend dashboard

**Goal:** visualize correlation gaps over time.
**Preconditions:** 4.1, 3.2.
**Build:** `components/TrendDashboard/`.

**Scenario tests (Playwright):**
- *A widening gap across multiple snapshots over time is reflected in the trend line's direction.*

**Definition of done:** passes.

---

### Step 4.6 — Leadership rollup view

**Goal:** display team/practice rollups.
**Preconditions:** 4.1, 3.4.
**Build:** `components/RollupView/`.

**Scenario tests (Playwright):**
- *A rollup below the privacy floor shows a clear withheld-state explanation, not blank or broken UI.*

**Definition of done:** passes.

---

### Step 4.7 — Full-journey Playwright suite

**Goal:** string together the practitioner and leadership journeys end-to-end against the full running stack.
**Preconditions:** all of Phase 4.
**Build:** `tests/scenarios/practitioner-journey.spec.ts`, `leadership-journey.spec.ts`.

**Scenario tests:**
- *Practitioner journey* — get a certification recommendation, accept it, request a path targeting it, attempt an item, see it reflected on the radar.
- *Leadership journey* — view a rollup, see an approved nudge's effect reflected the next time correlation runs.

**Definition of done:** both journeys pass against a full local stack (local Postgres + seeded data).

---

# Phase 5 — Hardening & Packaging

### Step 5.1 — Observability

**Goal:** a simple internal view over `agent_runs` — cost, latency, error rate.
**Preconditions:** 0.4 (data already exists from every prior step).
**Build:** an internal dashboard route/page reading `agent_runs`.

**Scenario tests:**
- *A recent agent error is surfaced in the observability view, including the error message.*

**Definition of done:** passes.

---

### Step 5.2 — Auth & access control

**Goal:** session-based auth for two roles. Practitioners: cookie session, no password. Admins/leadership: bcrypt password, forced change on first login. Each role sees only what it's entitled to.

**Preconditions:** every route that exposes data.
**Context to load:** `docs/architecture.md` (Auth & sessions section), `docs/data-model.md` (auth tables).

**Policy is already decided** — see `docs/architecture.md` §Auth & sessions for the full design. No 👤 judgment call remains; implement from spec.

**Build:**

*Backend:*
- Migration: `admin_users` and `sessions` tables (see `docs/data-model.md` §Auth tables).
- `backend/app/api/routes/auth.py`:
  - `POST /auth/practitioner-login` — body: `{ name, email, org_level }`. Upserts practitioner by email (name/level overwritten on re-entry). Creates session. Sets HTTP-only cookie. Returns `{ identity_type: "practitioner", first_name, practitioner_id }`.
  - `POST /auth/admin-login` — body: `{ email, password }`. Checks `admin_users`. Returns `{ identity_type: "admin", first_name, role, must_change_password }`. Sets HTTP-only cookie. Does NOT redirect — that's the frontend's job.
  - `POST /auth/logout` — clears the cookie and deletes the session row.
  - `POST /auth/change-password` — admin only; verifies current password, updates hash, sets `must_change_password = false`.
  - `GET /auth/me` — returns current session identity (used by frontend on page load to restore session context without re-login).
- `backend/app/api/deps/session.py`:
  - `get_session` — reads cookie, loads session row, attaches to `request.state`; returns 401 if missing/expired.
  - `require_practitioner` — calls `get_session`, 403 if `identity_type != practitioner`.
  - `require_admin` — calls `get_session`, 403 if `identity_type != admin` or `role != admin`.
  - `require_admin_or_leadership` — 403 if not an admin-type session.
- Apply the right dependency to every existing route (practitioners routes → `require_practitioner` with self-only enforcement; rollup/nudge routes → `require_admin_or_leadership`).
- Seed one starter admin: email `admin@example.com`, password `"welcome"`, `role = admin`, `must_change_password = true`.

*Frontend:*
- `frontend/src/pages/LoginPage.tsx` — landing page. Default state: practitioner form (name, email, org level). Checkbox "I'm an admin / leadership member" toggles to admin form (email, password). Submits to the right endpoint.
- `frontend/src/pages/ChangePasswordPage.tsx` — shown to admins when `must_change_password = true`. Blocks all other navigation until complete.
- `frontend/src/context/SessionContext.tsx` — React context, populated from `GET /auth/me` on app load. Holds `{ identityType, firstName, practitionerId?, adminRole? }`. Nav bar shows "Hi, [firstName]".
- Route guards: practitioner pages redirect to login if no session or wrong role; admin pages do the same.
- The existing "pick a practitioner" home page is replaced — a logged-in practitioner lands directly on their own tabs (Skill Radar, Certifications, Quiz, Trends).

**Scenario tests:**
- *A practitioner logs in by email and is routed directly to their own dashboard — no other practitioners' data is visible.*
- *Relaunching the app and re-entering the same email restores the same practitioner's learning history (paths, attempts, skill scores).*
- *A practitioner cannot fetch another practitioner's individual profile* — 403, not the data.
- *A leadership-role admin can view rollups and nudges but not an individual practitioner's raw attempts* — 403.
- *An admin with `must_change_password = true` is blocked from any data view until they change their password.*
- *An admin cannot log in with the wrong password* — 401.

**Definition of done:** all six scenario tests pass; the starter admin account exists in seed; `GET /auth/me` returns the right shape for both identity types.

---

### Step 5.3 — Deployment packaging

**Goal:** the whole stack runnable by someone who isn't you, from a clean checkout.
**Preconditions:** everything.
**Build:** Dockerfiles for backend and frontend (the app services — Postgres is expected as an external managed service), a filled-in `.env.example`, a README with setup steps.

**Scenario tests:**
- *A clean checkout comes up fully following the documented steps exactly* — ideally verified by actually doing it, not just trusting the README.

**Definition of done:** passes.

---

### Step 5.4 — Full regression pass + demo script

**Goal:** confirm nothing earlier broke, and have a repeatable demo.
**Preconditions:** everything.
**Build:** a literal, step-by-step demo script covering both journeys from 4.6.

**Scenario tests:** re-run the full scenario suite from every phase — zero regressions.
**Definition of done:** full suite green; the demo script runs start to finish without improvising.

---

### Step 5.5 — Bug fixes (pre-Phase 6 cleanup)

**Goal:** clear three known defects in the running app before the Phase 6 redesign begins. These are self-contained fixes with no schema changes; each can be verified manually in the running app within minutes.

**Preconditions:** 5.4 (app is running, seed data is present).

**Bug 1 — Quiz "Next" button loops on the same question**
Symptom: pressing "Next" after answering a question re-renders the same question instead of advancing to the next unanswered one. The item-selection index in `QuizRunner` is either not being incremented after a submission, or the items list is being re-fetched and resetting the index back to 0. Audit the interaction between `useItemsBySkill`, `useSubmitAttempt`, and whichever piece of state tracks "which item index is currently displayed."

**Bug 2 — Skill name text is invisible in the "Rate your skills" panel**
Symptom: skill names in `SelfAssessmentPanel` appear white-on-white in the skill rows (background `var(--surface-alt, #f9fafb)` is light, but `var(--text)` resolves to near-white in dark mode). The selected-state pill uses the hardcoded colour `"#111"` which also fails in dark mode. Fix: replace all hardcoded colour literals in `SelfAssessmentPanel` and its `LevelPicker` with CSS variables that honour both themes, and add a `@media (prefers-color-scheme: dark)` rule for `--surface-alt` so the row background is distinguishable in dark mode.

**Bug 3 — Top skill gaps bar chart does not update after quiz + regenerate**
Symptom: after submitting quiz attempts and clicking "Regenerate path", the radar polygon refreshes but the "Top skill gaps" progress bars in the side panel still show the old values. Both the radar and the bar chart read from the same `snapshots` data returned by `useSkillProfile` — if the radar is updating then the query key is being invalidated correctly. Investigate whether the bars are sorted from a stale copy of `snapshots` (e.g. a `useMemo` that doesn't depend on `snapshots`) or are rendering from a different, un-invalidated query.

**Scenario tests:** none automated — verified manually:
1. In the quiz, answer a question and confirm "Next" shows a different question.
2. In "Rate your skills", confirm all skill names and pill labels are readable in both light and dark mode.
3. After submitting quiz attempts and clicking "Regenerate path", confirm both the radar polygon *and* the top-gaps progress bars reflect the updated mastery scores.

**Definition of done:** all three bugs are fixed and manually verified.

---

# Phase 6 — Practitioner Profile Redesign

This phase replaces the ad-hoc "generate a path" flow with a deliberate, multi-profile practitioner experience. The central idea: a practitioner's **profile** is the union of their background answers, chosen certification goal, and self-rated skill levels. The Skill Radar and Quiz become read-driven views that consume the active profile; all authoring happens in the "Build my profile" flow. A practitioner can maintain multiple profiles (e.g. one for each cert they are considering), but only one is active at a time.

---

### Step 6.1 — Practitioner profile data model & API

**Goal:** introduce the `practitioner_profiles` table and the `profile_skill_assessments` table; link the existing certification goal and questionnaire answer records to a profile; add the CRUD + activation API.

**Preconditions:** 5.5.
**Context to load:** `docs/data-model.md`, `docs/architecture.md`.

**Build:**

*Schema (new migration):*
- `practitioner_profiles`: `id` (UUID PK), `practitioner_id` (FK → practitioners), `name` (text, user-chosen label e.g. "My AWS path"), `is_active` (bool, default false), `certification_id` (nullable FK → certifications), `questionnaire_snapshot` (JSONB — a verbatim copy of the questionnaire answers at save time), `created_at`, `updated_at`. Constraint: at most one row per `practitioner_id` may have `is_active = true` (enforced in application logic, not DB constraint, to keep the activation swap atomic).
- `profile_skill_assessments`: `id` (UUID PK), `profile_id` (FK → practitioner_profiles, ON DELETE CASCADE), `skill_id` (FK → skills), `signal_strength` (float, 0.0–1.0), `updated_at`. Unique constraint on `(profile_id, skill_id)` — one row per skill per profile, upserted on re-save.
- Add nullable `profile_id` (FK → practitioner_profiles) to `certification_advisor_responses` and `practitioner_certification_goals`. Existing rows are left null.

*API routes (backend):*
- `POST /practitioners/{id}/profiles` — create a profile with `name`, `questionnaire_snapshot`, and optional `certification_id`. Returns the new profile. Does not activate automatically.
- `GET /practitioners/{id}/profiles` — list all profiles for the practitioner, ordered by `created_at` desc. Each item includes the certification code (if set) and the latest mastery aggregate % (computed from the last skill-profile snapshot).
- `GET /practitioners/{id}/profiles/{profile_id}` — full detail: profile fields + `profile_skill_assessments` list.
- `PATCH /practitioners/{id}/profiles/{profile_id}` — update `name`, `certification_id`, or `questionnaire_snapshot`.
- `PATCH /practitioners/{id}/profiles/{profile_id}/activate` — set `is_active = true` on this profile and `is_active = false` on all others for the same practitioner, atomically. Returns the updated profile.
- `POST /practitioners/{id}/profiles/{profile_id}/skill-assessments` — upsert skill ratings (list of `{skill_id, signal_strength}`). Returns `{rows_written: N}`.

*Skill Profiler integration:* when the Skill Profiler workflow runs, it should look up the practitioner's active profile. If one exists, its `profile_skill_assessments` rows are included as self-assessment signals alongside any `skill_profile_events` of other sources. If no profile exists, the existing fallback (loose `skill_profile_events` of type `self_assessment`) continues to work.

**Scenario tests:**
- *A practitioner can have many profiles but only one active at a time* — activating a second profile atomically deactivates the first; a third `GET /profiles` confirms exactly one `is_active = true` row.
- *The Skill Profiler uses the active profile's skill assessments as input* — Given an active profile with `signal_strength = 0.75` on skill X and no other signals, when the profiler runs, skill X's mastery score in the snapshot is materially above zero.
- *Switching the active profile and re-profiling produces a different radar* — Given two profiles with different ratings on skill X (0.25 vs 0.75), activating each and running the profiler in sequence yields different `mastery_score` values in the snapshot.

**Definition of done:** all three pass; migration runs clean against local DB; existing seeded data is not disrupted.

---

### Step 6.2 — Enhanced practitioner questionnaire 👤

**Goal:** extend the four-question certification advisor form into a richer background questionnaire that both improves the recommendation quality and becomes the stored `questionnaire_snapshot` on the profile.

**Preconditions:** 6.1.
**Context to load:** `docs/architecture.md` (Certification Advisor section), `docs/human-in-the-loop.md`.

**Build:**
- Extend the questionnaire schema (backend Pydantic type + frontend TypeScript type) with additional optional fields covering: years of AI/ML experience (`none` / `under_1` / `1_to_3` / `over_3`), primary job role (`developer` / `architect` / `consultant` / `manager` / `researcher` / `other`), whether they currently deploy LLMs in production (`bool`), self-rated prompt-engineering familiarity (`none` / `basic` / `intermediate` / `advanced`), and whether they manage or mentor others on AI topics (`bool`).
- Update the Certification Advisor agent prompt (`agents/prompts/certification_advisor.md`) to incorporate the new signals — e.g., a manager who mentors others, has no coding background, and rates their prompt-engineering as "basic" should trend toward CCAO-F even without an explicit provider preference.
- Backward compatibility: the four original fields (`provider_preference`, `writes_code`, `focus_area`, `experience_level`) remain required; the new five fields are optional so stored responses from before this step don't break.
- The questionnaire snapshot stored on the profile should include all fields (original + new).

**Scenario tests:**
- *A manager who mentors others and has no coding experience is recommended CCAO-F even without a provider preference* — the new signals push the advisor toward the non-coding track.
- *All new questionnaire fields survive a round-trip* — POST a profile with all fields populated; GET the profile back; every field matches exactly.

**Definition of done:** both pass.

> 👤 **Human-in-the-loop:** review the final question wording and the updated advisor prompt before implementing. The questions only improve the recommendation if they are clearly worded; the prompt only uses them correctly if the weighting is deliberate. See `docs/human-in-the-loop.md`.

---

### Step 6.3 — "Build my profile" landing page

**Goal:** replace the current post-login landing for practitioners with a page that surfaces their profiles and is the starting point for all profile creation and editing.

**Preconditions:** 6.1.
**Context to load:** `docs/architecture.md` (Frontend section).

**Build:**
- New page `frontend/src/pages/BuildProfilePage.tsx`, routed at `/profile`.
- **Empty state** (no profiles yet): a prominent "Build your first profile" headline, a two-sentence explanation of what a profile is, and a single "Start" CTA that launches the profile wizard (Step 6.4).
- **With profiles**: a responsive card grid — one card per profile. Each card shows: profile name, certification code + full name (or "No certification chosen"), last radar date, a mastery progress bar (aggregate % toward the cert's skills), and an "Active" badge on the currently active profile. Card actions: **Activate** (visible only on inactive profiles), **Edit** (re-enters the wizard with answers pre-populated), **Delete** (with a confirm dialog; disabled if it is the only profile).
- A "New profile" button in the page header always launches the wizard from scratch.
- Routing: practitioners land on `/profile` immediately after login (redirect from the root `/`). The nav bar gains a "My Profiles" link for practitioners.
- The existing tabs (Skill Radar, Quiz, Certifications, Trends) remain accessible from the nav bar; this page is the default view after login, not a replacement for the tabs.

**Scenario tests (Playwright):**
- *A new practitioner lands on `/profile` after login and sees the empty-state CTA, not a broken chart.*
- *A practitioner with two profiles sees two cards; the active one carries the "Active" badge.*

**Definition of done:** both pass.

---

### Step 6.4 — Profile questionnaire + certification selection wizard

**Goal:** the multi-step wizard that collects background answers, gets a certification recommendation, and lets the practitioner confirm or override the choice — producing a saved (but not yet active) profile by the end.

**Preconditions:** 6.2, 6.3.

**Build:**
- Multi-step wizard component `frontend/src/components/ProfileBuilder/ProfileWizard.tsx`:
  - **Step 1 — About you**: Profile name (free text) + all questionnaire fields from Step 6.2 (original four + new five). A progress indicator shows "Step 1 of 3".
  - **Step 2 — Certification choice**: A "Get recommendation" button calls `POST /certification-advisor` with the questionnaire answers → displays the recommended certification with its rationale. Below the recommendation, shows the full list of available certifications (grouped by provider) so the practitioner can accept the recommendation or pick a different one. Selecting a certification highlights it; the CTA changes to "Continue with [cert code]".
  - **Step 3 — Confirm**: A read-only summary card showing the chosen profile name and certification. A "Continue to skill rating →" CTA saves the profile to the backend (`POST /practitioners/{id}/profiles`) and navigates to Step 6.5 (skill assessment) with the new `profile_id` in the URL.
- Back-navigation between wizard steps preserves all entered values (no data loss on pressing "Back").
- When the wizard is entered via "Edit" on an existing profile card, all fields are pre-populated from the existing `questionnaire_snapshot` and `certification_id`; saving calls `PATCH /practitioners/{id}/profiles/{profile_id}`.

**Scenario tests (Playwright):**
- *Completing the wizard creates a profile with the chosen certification attached — the profile appears on `BuildProfilePage`.*
- *Choosing a different certification than the recommendation saves the override correctly.*
- *Pressing "Back" from Step 2 to Step 1 preserves the answers already entered.*

**Definition of done:** all three pass.

---

### Step 6.5 — Profile-linked skill assessment

**Goal:** after the wizard commits a certification choice, present a skills table weighted toward that certification's skills and save the ratings against the profile.

**Preconditions:** 6.4.

**Build:**
- New page/view `frontend/src/pages/ProfileSkillAssessmentPage.tsx`, routed at `/profile/:profileId/skills`.
- Skills are displayed in two tiers:
  - **Tier 1 — Certification-relevant skills** (shown first, with a subtle cert-name badge next to the section header): all skills in `certification_skills` for the profile's chosen certification, sorted alphabetically within tier.
  - **Tier 2 — All other catalog skills** (shown below a divider): the remaining skills, also sorted alphabetically.
- For a brand-new profile, all skills default to "None". For an existing profile being edited, pre-populate from `profile_skill_assessments` rows.
- The `SelfAssessmentPanel` component is refactored or replaced by a new `ProfileSkillRater` component that accepts `certificationId` and renders the two-tier layout.
- "Save assessment" calls `POST /practitioners/{id}/profiles/{profile_id}/skill-assessments`. On first save of a profile that has no prior active profile, the backend also calls `PATCH /…/activate` to make this the active profile automatically. On subsequent saves it is an upsert only.
- After saving: navigate back to `BuildProfilePage` with a "Profile saved and activated" toast.

**Scenario tests:**
- *Saving skill ratings creates exactly one `profile_skill_assessments` row per skill in the catalog (none duplicated).*
- *Certification-relevant skills appear before non-certification skills in the rendered table.*
- *Re-saving updated ratings upserts — row count stays the same, values update.*

**Definition of done:** all three pass.

---

### Step 6.6 — Profile management & activation

**Goal:** complete the profile-switching experience — practitioners can activate any profile from the list, and the rest of the app (Skill Radar, Quiz) immediately reads from the newly active one.

**Preconditions:** 6.5.

**Build:**
- "Activate" button on profile cards (Step 6.3) calls `PATCH /practitioners/{id}/profiles/{profile_id}/activate`, then invalidates the profiles list query and the skill-profile snapshot query so both `BuildProfilePage` and the Skill Radar tab reflect the change without a full page reload.
- The active profile's certification code is exposed on the `GET /auth/me` response (add `active_profile_id` and `active_certification_code` to the `MeResponse` schema) so any tab can read it without an extra round-trip.
- The nav bar shows the active certification code as a small badge next to "My Profiles" (e.g. "My Profiles · CCAF") so the practitioner always knows which profile is driving their experience.
- "Delete" on a profile card: disabled if it is the currently active profile or if it is the only profile. Shows a confirm dialog; on confirm calls `DELETE /practitioners/{id}/profiles/{profile_id}` (new endpoint — cascades to `profile_skill_assessments`).

**Scenario tests:**
- *Activating profile B from `BuildProfilePage` deactivates profile A — the Active badge moves, the Skill Radar and Quiz tabs now read from profile B's data.*
- *Deleting a non-active profile removes it from the list without affecting the active profile.*

**Definition of done:** both pass; verified manually in the running app.

---

### Step 6.7 — Skill Radar enhancements

**Goal:** turn the Skill Radar tab into a clean, read-only dashboard that communicates certification progress and guides the practitioner toward their next action.

**Preconditions:** 6.6.

**Build:**
- **Remove** the "✏ Rate your skills" toggle from the Skill Radar tab entirely — skill rating now lives in the Profile Builder. Replace it with a small "Edit profile →" link that navigates to `BuildProfilePage`.
- **Aggregate mastery card**: a new card above (or to the side of) the radar showing `"Progress toward [cert code]: XX%"` — computed as `mean(mastery_score)` across the certification's skills in the active snapshot. Include a progress bar. If no certification is set on the active profile, omit this card and show the existing radar header unchanged.
- **Guidance message** (below the aggregate card, driven by the aggregate %):
  - **< 40 %**: "Keep building — take more quizzes and update your skill self-assessment to give the radar a fuller picture."
  - **40 – 69 %**: "Good progress. Focus on the weakest skills shown above and keep answering quizzes in those areas."
  - **70 – 89 %**: "You're getting close. Review the remaining gaps and aim for a practice run soon."
  - **≥ 90 %**: "Strong profile — you look ready to schedule your certification exam."
- The radar title becomes **"Skill profile — [cert code]"** when an active certification is set; falls back to **"Skill profile"** otherwise.
- "Regenerate path" CTA remains; add a caption beneath it: *"Updates after you answer quizzes or edit your profile."*

**Scenario tests (Playwright):**
- *A practitioner with all mastery scores at 0 % sees the "< 40 %" guidance message.*
- *A practitioner whose cert-relevant skills average above 90 % sees the "ready" message.*
- *The "Rate your skills" toggle button is absent from this tab.*

**Definition of done:** all three pass.

---

### Step 6.8 — Quiz profile-awareness & navigation fix

**Goal:** quiz questions are drawn from the active profile's certification-relevant skills first; the Next button reliably advances to the next unanswered question.

**Preconditions:** 6.6.

**Build:**

*Bug 1 fix (carry-over from 5.5 if not yet done) — Next button loops:* audit `QuizRunner`. The most likely cause is that `useItemsBySkill` re-fetches (resetting to the first item) each time an attempt is submitted, or the selected-item index is stored in a piece of state that the `onSuccess` callback inadvertently resets. Fix the index management so "Next" consistently advances to the next item in the fetched list and does not reset on submission.

*Profile-aware skill ordering:* the skill selector in the Quiz tab reads the active profile's `certification_id` (available from the `MeResponse` added in Step 6.6). Certification-relevant skills are sorted to the top of the skill list with a `(cert)` tag; non-cert skills appear below. Default skill on tab open is the weakest cert-relevant skill by mastery score (same ordering as the learning path).

*Fallback:* if no active profile or no certification set, the quiz behaves as before — all skills, weakest-first.

**Scenario tests (Playwright):**
- *Answering a question and pressing "Next" advances to a different question every time — the same question is never shown twice in a row.*
- *A practitioner with an active certification profile sees that cert's skills listed first in the quiz skill selector, tagged "(cert)".*

**Definition of done:** both pass.
