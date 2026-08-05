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
- [ ] 1.1 `mcp-learning-portal` MCP server
- [ ] 1.2 `mcp-usage-signals` MCP server 👤

**Phase 2 — Mastery Mesh (learning loop)**
- [ ] 2.1 Skill graph & practitioner profile API
- [ ] 2.2 Certification catalog + seed data
- [ ] 2.3 Certification Advisor Agent 👤
- [ ] 2.4 Skill Profiler Agent
- [ ] 2.5 Curriculum Planner Agent
- [ ] 2.6 Item-Writer Agent 👤
- [ ] 2.7 Grader Agent 👤
- [ ] 2.8 Learning-path orchestrator workflow + API

**Phase 3 — Adoption Pulse (signal loop)**
- [ ] 3.1 Usage-Signal Agent
- [ ] 3.2 Correlation Agent 👤
- [ ] 3.3 Nudge Composer Agent 👤
- [ ] 3.4 Rollup Reporter Agent 👤
- [ ] 3.5 Nightly Pulse orchestrator workflow
- [ ] 3.6 API routes for the pulse loop

**Phase 4 — Frontend**
- [ ] 4.1 App shell, routing, typed API client
- [ ] 4.2 Certification Advisor questionnaire UI
- [ ] 4.3 Skill Radar dashboard
- [ ] 4.4 Quiz Runner (trap-reveal) 👤
- [ ] 4.5 Adoption trend dashboard
- [ ] 4.6 Leadership rollup view
- [ ] 4.7 Full-journey Playwright suite

**Phase 5 — Hardening & Packaging**
- [ ] 5.1 Observability
- [ ] 5.2 Auth & access control 👤
- [ ] 5.3 Deployment packaging
- [ ] 5.4 Full regression pass + demo script

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
- `docker-compose.yml` with a Postgres service (`pgvector/pgvector` image so the extension is available later).
- `.env.example`, `.gitignore` (`node_modules`, `.venv`, `__pycache__`, `.env`), a `README.md` stub pointing at `CLAUDE.md` and this file.

**Scenario tests:** none yet — this step is scaffolding, not behavior.
**Definition of done:** `docker compose up -d` brings up Postgres; `cd backend && pytest` runs cleanly with zero tests; `cd frontend && npm run build` succeeds on the default template.

---

### Step 0.2 — Database schema v1 + migrations

**Goal:** the first migration, covering only what Phase 0–2 need: `practitioners`, `skills`, `skill_profile_events`, `skill_profile_snapshots`, `agent_runs`, `workflow_runs`. The rest of `docs/data-model.md` comes in later, smaller migrations — easier to reason about and to reverse.
**Preconditions:** 0.1.
**Context to load:** `docs/data-model.md` (full).
**Build:** SQLAlchemy models for the six tables above; one Alembic migration.

**Scenario tests:**
- *Running migrations twice is safe* — Given a fresh database, when `alembic upgrade head` runs twice in a row, then the second run makes no changes and exits cleanly.
- *Downgrade reverses cleanly* — Given the migration has been applied, when `alembic downgrade base` runs, then none of this migration's tables remain.

**Definition of done:** both scenarios pass; `alembic upgrade head` runs clean on a fresh `docker compose` Postgres.

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

**Definition of done:** both journeys pass against a full local stack (`docker compose` + seeded data).

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

### Step 5.2 — Auth & access control 👤

**Goal:** role-based access — practitioners see their own data; leadership sees aggregates only.
**Preconditions:** every route that exposes data.
**Context to load:** `docs/human-in-the-loop.md`.
**Build:** auth middleware, role checks on routes — 👤 decide the actual policy before writing the checks.

**Scenario tests:**
- *A practitioner cannot fetch another practitioner's individual profile* — 403, not the data.
- *A leadership-role user can view a rollup but not an individual's raw attempts* — 403.

**Definition of done:** both pass.

> 👤 **Human-in-the-loop:** get this wrong before real practitioners are in the system and it's a trust problem, not a bug report. Decide the policy yourself. See `docs/human-in-the-loop.md`.

---

### Step 5.3 — Deployment packaging

**Goal:** the whole stack runnable by someone who isn't you, from a clean checkout.
**Preconditions:** everything.
**Build:** Dockerfiles for backend/frontend, a complete `docker-compose.yml`, a filled-in `.env.example`, a README with setup steps.

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
