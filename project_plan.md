# Mastery Pulse — Project Plan

## How to use this document for this project

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

**Phase 7 — Smart Nudge System**
- [x] 7.1 Nudge data model expansion & API
- [x] 7.2 Nudge Category Generator Agent 👤
- [x] 7.3 Nudge Campaign workflow (recipient resolution + composition)
- [x] 7.4 Admin/Leadership Nudge Management UI
- [x] 7.5 Practitioner Nudge Inbox & Progress Trend Chart
- [x] 7.6 Email delivery integration
- [x] 7.7 End-to-end Nudge Playwright suite

**Phase 8 — Multi-Model Provider Support (NVIDIA Nemotron)**
- [x] 8.1 Configuration & model abstraction layer
- [x] 8.2 NVIDIA Nemotron client implementation
- [x] 8.3 Agent framework integration
- [x] 8.4 MCP server compatibility
- [x] 8.5 Testing & validation
- [x] 8.6 Documentation & migration guide

**Phase 9 — Mastery Refinements: Quiz-Driven Radar, Profile Lockdown & Admin Simplification**
- [x] 9.1 Remove Rollups & nightly auto-nudge pipeline
- [x] 9.2 Admin/Leadership practitioner view — Skill Radar only (read-only)
- [x] 9.3 Profile lockdown after first full submission
- [x] 9.4 Quiz-only mastery engine (Skill Radar driven solely by quiz answers)
*(Steps 9.5–9.7 merged into Phase 10 — see below)*

**Phase 10 — Certification-Domain Alignment & Mastery Refinements**
- [x] 10.1 Certification exam domains data model & seed data 👤
- [x] 10.2 Domain versioning data model — live-refreshable domain versions
- [x] 10.3 Cert Domain Discovery Agent — LLM-driven exam domain research & refresh 👤
- [x] 10.4 Admin "Refresh Certification Domains" UI
- [x] 10.5 Domain Scorer Agent — self-assessment → initial domain scores
- [x] 10.6 Domain-aware item writer & tagging 👤
- [x] 10.7 Progressive quiz-round scoring model (scores can rise AND fall)
- [x] 10.8 Auto-refresh quiz questions after round exhaustion
- [x] 10.9 Certification domain gap scoring workflow & UI
- [x] 10.10 Quiz UI certification-domain awareness (color-coded tabs)
- [x] 10.11 Visual mastery trend indicators (↑ green / ↓ amber on radar + domain chart)

**Phase 11 — Mock Exam System**
- [x] 11.1 Exam config data model, migration & seed (question count, duration, passing score per cert)
- [x] 11.2 MockExamGenerator Agent + mock exam API routes (create / pause / resume / answer / complete)
- [x] 11.3 Quiz tab answered-questions log + stable tab ordering
- [x] 11.4 Skill Radar 80%-mastery CTA + MockExamPage (timer, instant feedback, completion recording)

**Phase 12 — Quiz Generation: Decoupled, Batched, Fast**
- [x] 12.1 Decouple ItemWriter from path generation — path generation becomes < 30 s
- [x] 12.2 QuizBatchGeneratorAgent — one LLM call generates 1 starter question per skill for the whole path
- [x] 12.3 Quiz tab loading UX — "Generating quiz…" screen on first open; all tabs populate at once when batch completes

**Phase 13 — Dynamic Cert Skill Discovery & Domain-Weighted Radar**
- [x] 13.1 DB schema — extend `certification_skills` with domain linkage and source provenance
- [x] 13.2 CertSkillMapperAgent — web-research cert blueprint → 10–12 skills aligned to exam domains 👤
- [x] 13.3 Profile creation hook — trigger skill mapping at profile lock; admin refresh endpoint
- [x] 13.4 Domain-weighted Skill Radar — radar nodes colored by domain weight
- [x] 13.5 80/20 enforcement — quiz batch ratio audit in QuizBatchGeneratorAgent

**Phase 14 — Provider Resilience: Haiku Fallback & Graceful Degradation**
- [x] 14.1 Haiku-pinned Anthropic client — force `claude-haiku-4-5-20251001` for all Anthropic calls
- [x] 14.2 `FallbackModelClient` — NVIDIA (45 s) → Haiku (30 s) two-tier call chain
- [x] 14.3 Graceful degraded domain scoring + `domain_scoring_status` column
- [x] 14.4 DB migration + ORM model for `domain_scoring_status`
- [x] 14.5 Frontend `domain_scoring_status` awareness (radar + domain gap badge)
- [x] 14.6 Render env-var checklist & documentation freeze

**Phase 15 — Three-Tier Provider Chain with Circuit Breaker**
- [x] 15.1 Three-tier `MultiTierModelClient` — Ultra (10 s) → Lightning (20 s) → Haiku (20 s) → degraded
- [x] 15.2 In-memory circuit breaker — skip NVIDIA after 5 consecutive failures; 2-minute cooldown
- [x] 15.3 Reversed chain for `APP_BRAIN_MODEL=ANTHROPIC` — Haiku (10 s) → Ultra (20 s) → Lightning (20 s)
- [x] 15.4 `.env` + config update — `NVIDIA_MODEL_ID_PRIMARY`, `NVIDIA_MODEL_ID_SECONDARY`, per-tier timeouts
- [x] 15.5 Graceful degraded response — informative 503 when all three tiers fail
- [x] 15.6 Documentation freeze — update `docs/MULTI_PROVIDER.md` and `docs/architecture.md`

**Phase 16 — Instant MCQ Feedback (Pre-generated Rationales)**
- [x] 16.1 Extend `MCQAnswerKey` schema — add optional `correct_rationale` and `incorrect_rationale` fields
- [x] 16.2 Update `QuizBatchGeneratorAgent` prompt — LLM generates both rationales at question-creation time
- [x] 16.3 Update `ItemWriter` prompt — auto-refresh path also generates rationales
- [x] 16.4 Deterministic MCQ grading in `POST /attempts` — `_grade_mcq_instantly()` picks pre-written rationale; no LLM call for Phase 16 items
- [x] 16.5 Graceful fallback for legacy items — if rationale fields absent, route falls through to `GraderAgent`
- [x] 16.6 Scenario tests — 20 tests covering correct/incorrect/trap scoring, boundary cases, schema backward-compat, and GraderAgent fallback trigger
- [x] 16.7 Documentation freeze — update `docs/architecture.md`, `docs/data-model.md`, `project_plan.md`

**Phase 17 — Continuous Quiz: Progressive Per-Skill Background Generation**
- [x] 17.1 `GenerateLearningPathResponse` — add `quiz_generating` and `quiz_skipped_reason` fields
- [x] 17.2 `SkillQuizSpec` — add `question_count` (1 or 2) and `prior_prompts` fields; update `_build_messages` and agent docstring
- [x] 17.3 `QuizBatchGeneratorAgent` prompt — per-spec `question_count` rules, no-repeat constraint, Phase 16 rationale fields
- [x] 17.4 Route helpers — `_check_quiz_exhaustion`, `_compute_skill_avg_scores`, `_assign_question_counts`
- [x] 17.5 DB migration — add `quiz_status VARCHAR(20) DEFAULT 'pending'` to `learning_path_items`; values: `pending | ready | failed`; seeded as `'pending'` when a path item row is created
- [x] 17.6 Background engine — `_generate_quizzes_progressively`; one LLM call per skill; 1-2 questions per call (~700-1400 output tokens; fits NVIDIA); on success: set `quiz_status='ready'` and persist items; on exception: set `quiz_status='failed'`, log warning, continue to next skill; uses a fresh DB session (request session already closed)
- [x] 17.7 `POST /learning-paths/generate` — fire background task via FastAPI `BackgroundTasks`; return path immediately; `quiz_generating=True`; no blocking wait for quiz completion
- [x] 17.8 `POST /quiz-batch` — admin/recovery wrapper (synchronous, awaited)
- [x] 17.9 `POST /practitioners/{id}/quiz-generation/retry` — fetch active path; filter `learning_path_items` where `quiz_status='failed'`; reset each to `'pending'`; fire a new background task for only those skills; idempotent (noop if no failed items)
- [x] 17.10 Frontend three-state quiz tab — poll `GET /items` + learning path every 5 s; **ready** (items in DB): render questions normally; **pending** (status=`pending`, no items): ⏳ dimmed tab, "Questions being prepared…"; **failed** (status=`failed`, no items): ⚠️ amber tab, "Generation failed"; "↻ Retry Failed Skills" button shown at tab-group top when any skill is `failed`; stop polling once all skills are either `ready` or `failed`
- [x] 17.11 Reduce `QuizBatchGeneratorAgent.max_tokens` to 3000 (1 skill × max 2 questions ≈ 1400 output tokens; prevents NVIDIA reserving excess compute time)
- [x] 17.12 Scenario tests — background invocation, per-skill error recovery, failure status persisted, retry re-queues only failed skills, all-ready stops polling
- [x] 17.13 Documentation freeze

---

# Phase 14 — Provider Resilience: Haiku Fallback & Graceful Degradation

**Why this phase exists.**  NVIDIA's Nemotron Ultra endpoint has two documented failure modes: (1) slow-but-degraded calls that can hang for 20+ minutes before returning a garbage structured-output response, and (2) hard 400 "DEGRADED function cannot be invoked" errors.  Both leave practitioners staring at a frozen "Saving…" spinner.  The fix is a two-tier fallback chain — NVIDIA primary → Anthropic Haiku secondary — and a mechanical fallback when both providers fail, so the profile lock always completes in under 2 minutes regardless of API health.

**Anthropic model constraint (this deployment).**  All Anthropic calls — whether as primary provider or as fallback — use `claude-haiku-4-5-20251001` exclusively.  No Sonnet, Opus, or Fable calls.  This is non-negotiable for cost control; the owner has a paid Anthropic key and does not want surprise charges.  See `docs/MULTI_PROVIDER.md` for the full model override strategy.

**Preconditions:** Phase 13 Definition of Done is met.

---

### Step 14.1 — Haiku-pinned Anthropic client

**Goal:** all Anthropic API calls — regardless of what model string individual agents carry — are routed to `claude-haiku-4-5-20251001`.  Today agents hardcode `model = "claude-sonnet-5"` as a class attribute; the NVIDIA client already ignores that string and uses its own `_model_id`.  Anthropic must do the same.

**Context to load:** `docs/MULTI_PROVIDER.md`, `backend/app/agents/model_client.py`, `backend/app/agents/base.py`.

**Build:**

1. **`AnthropicModelClient` — add `model_id` parameter** (default `"claude-haiku-4-5-20251001"`):
   ```python
   class AnthropicModelClient(BaseModelClient, ModelClient):
       def __init__(self, api_key: str, model_id: str = "claude-haiku-4-5-20251001") -> None:
           ...
           self._model_id = model_id
   ```
   `AnthropicMessagesClient.parse()` uses `self._model_id` instead of the `model` arg passed by the agent (identical pattern to `NVIDIAMessagesClient`).

2. **`create_model_client()` factory** — when `APP_BRAIN_MODEL=ANTHROPIC`, instantiate `AnthropicModelClient(api_key=..., model_id="claude-haiku-4-5-20251001")`.  The `model_id` is read from a new `APP_ANTHROPIC_MODEL_ID` setting (default `"claude-haiku-4-5-20251001"`) so it can be overridden in `.env` without a code change.

3. **`effective_model` in `base.py`** — already detects `_model_id` on the client and returns it.  No change needed; `agent_runs.model_used` will automatically show `claude-haiku-4-5-20251001` instead of `claude-sonnet-5`.

4. **Update `docs/MULTI_PROVIDER.md`** — add `APP_ANTHROPIC_MODEL_ID` to the configuration reference; note Haiku constraint.

**Scenario tests:**
- *Anthropic client uses Haiku model* — Given `APP_BRAIN_MODEL=ANTHROPIC`, when any agent runs with a stub Anthropic client, then `agent_runs.model_used` equals `"claude-haiku-4-5-20251001"`, never `"claude-sonnet-5"`.
- *`effective_model` reflects actual model* — Given an `AnthropicModelClient` with `model_id="claude-haiku-4-5-20251001"`, when `agent.effective_model` is read, then it returns `"claude-haiku-4-5-20251001"`.

**Definition of done:** all existing scenario tests pass unchanged.  `agent_runs.model_used` shows `claude-haiku-4-5-20251001` for any agent run against an Anthropic client.

---

### Step 14.2 — `FallbackModelClient` — NVIDIA (45 s) → Haiku (30 s) two-tier call chain

**Goal:** when `APP_BRAIN_MODEL=NVIDIA` and `ANTHROPIC_API_KEY` is present, every agent call flows through a two-tier chain: NVIDIA first (45 s hard timeout, 1 attempt), Anthropic Haiku second (30 s hard timeout, 1 attempt), then raises `ProviderUnavailableError` if both fail.  The chain is transparent to agents — they receive a `ModelClient` and call `.parse()` as normal.

**Context to load:** `docs/architecture.md` §Provider Resilience, `backend/app/agents/model_client.py`.

**Build:**

1. **`ProviderUnavailableError`** — new exception in `model_client.py`:
   ```python
   class ProviderUnavailableError(RuntimeError):
       """Raised when every tier of the fallback chain has been exhausted."""
       def __init__(self, primary_error: BaseException, fallback_error: BaseException | None = None):
           self.primary_error = primary_error
           self.fallback_error = fallback_error
           super().__init__(
               f"All providers unavailable. Primary: {primary_error}. "
               f"Fallback: {fallback_error}"
           )
   ```

2. **`FallbackModelClient`** — wraps a primary and an optional fallback client:
   ```python
   class FallbackModelClient(ModelClient):
       """Tries primary; on failure tries fallback; raises ProviderUnavailableError if both fail."""
       def __init__(self, primary: ModelClient, fallback: ModelClient | None = None) -> None:
           ...
       async def parse(self, *, model, system, messages, max_tokens, output_format, **kwargs):
           try:
               result = await asyncio.wait_for(
                   self._primary.parse(...), timeout=45.0
               )
               self._last_model_used = getattr(self._primary, "_model_id", model)
               return result
           except Exception as primary_exc:
               # log WARNING with primary error
               if self._fallback is None:
                   raise ProviderUnavailableError(primary_exc)
               try:
                   result = await asyncio.wait_for(
                       self._fallback.parse(...), timeout=30.0
                   )
                   self._last_model_used = getattr(self._fallback, "_model_id", "haiku-fallback")
                   return result
               except Exception as fallback_exc:
                   raise ProviderUnavailableError(primary_exc, fallback_exc)
   ```

3. **`effective_model` in `base.py`** — detect `FallbackModelClient` and return `_last_model_used` (the tier that actually responded).  Unset before a call = report the primary model ID.

4. **`create_model_client()` factory** — when `APP_BRAIN_MODEL=NVIDIA`:
   - If `ANTHROPIC_API_KEY` is set → return `FallbackModelClient(primary=NVIDIAModelClient(...), fallback=AnthropicModelClient(api_key=..., model_id="claude-haiku-4-5-20251001"))`
   - If `ANTHROPIC_API_KEY` not set → return `NVIDIAModelClient(...)` as before (no fallback; degraded path kicks in at the endpoint level in Step 14.3)

5. **Per-tier timeouts on the underlying clients** — `NVIDIAModelClient` keeps `timeout=45.0` on the `AsyncOpenAI` client (set in Phase 13 bug fix).  `AnthropicModelClient` gets `timeout=30.0` on the `AsyncAnthropic` client.  The `wait_for` in `FallbackModelClient` is a belt-and-suspenders guard on top.

6. **Remove exponential-backoff retries on the primary** — set `NVIDIAModelClient._transient_errors = ()` (empty tuple).  With the fallback chain, retrying a slow NVIDIA call wastes time the Haiku fallback could already be using.  One attempt per tier; if it fails, move on.

**Scenario tests (stub clients):**
- *Primary succeeds* — Given a `FallbackModelClient` where primary returns a valid response, when `.parse()` is called, then result equals primary's response and `_last_model_used` equals primary model ID.
- *Primary fails → fallback succeeds* — Given primary raises `openai.APITimeoutError` and fallback returns a valid response, when `.parse()` is called, then result equals fallback's response, `_last_model_used` equals `"claude-haiku-4-5-20251001"`, and a WARNING is logged naming the primary failure.
- *Both fail → ProviderUnavailableError* — Given both primary and fallback raise exceptions, when `.parse()` is called, then `ProviderUnavailableError` is raised containing both errors.

**Definition of done:** all three scenario tests green.  `agent_runs.model_used` shows correct tier.  No existing scenario tests broken.

---

### Step 14.3 — Graceful degraded domain scoring

**Goal:** when both providers fail during profile lock (i.e., `ProviderUnavailableError` is raised by the Domain Scorer call), the profile still locks cleanly.  Domain scores are estimated mechanically from self-assessment signal strengths (no LLM), and the profile is flagged so the frontend can show a "Scores estimated" badge.  The practitioner is never left with a spinner.

**Context to load:** `backend/app/api/routes/profiles.py` (the `upsert_skill_assessments` endpoint), `docs/data-model.md` §`certification_domain_scores`.

**Mechanical scoring formula (no LLM):**

For each certification domain in the profile's locked version:
1. Collect all `profile_skill_assessments` for this profile (skill_name → signal_strength 0–1).
2. If `agent_discovered` certification_skills rows exist for the cert with a `certification_domain_id` matching this domain → average their signal strengths.  Otherwise → average all assessments (domain-agnostic fallback).
3. Cap the result at 0.5 (same confidence cap as the LLM-derived `self_assessment_estimate`).
4. Write to `certification_domain_scores` with `source = 'degraded_estimate'` and `confidence = 0.3`.
5. Set `practitioner_profiles.domain_scoring_status = 'degraded'`.

**Build:**

1. **Wrap the Domain Scorer call** in `upsert_skill_assessments`:
   ```python
   try:
       scorer_output = await scorer.run(scorer_input)
       # ... persist LLM scores as today ...
       profile.domain_scoring_status = "lm_scored"
   except ProviderUnavailableError:
       _compute_degraded_domain_scores(profile, cert_domains, skill_assessments, db)
       profile.domain_scoring_status = "degraded"
       logger.warning("Domain Scorer unavailable — using mechanical estimate for profile %s", profile.id)
   ```

2. **`_compute_degraded_domain_scores()`** — pure-Python helper in `profiles.py`; no DB writes other than via the passed `db` session.

3. **`certification_domain_scores.source`** gains a new valid value: `'degraded_estimate'`.  Add to the check constraint in the next migration (Step 14.4).

4. **CertSkillMapper hook (Phase 13.3)** — already has a try/except + `asyncio.wait_for(timeout=60)`.  No change needed; it silently skips if both providers fail, using seed skills.  The 60 s timeout stays.

**Scenario tests:**
- *Domain Scorer succeeds* — Given both providers healthy, when `upsert_skill_assessments` runs, then `profile.domain_scoring_status = 'lm_scored'` and all `certification_domain_scores` have `source = 'self_assessment_estimate'` or `'quiz_derived'`.
- *Both providers fail* — Given Domain Scorer raises `ProviderUnavailableError`, when `upsert_skill_assessments` runs, then profile is still locked (`is_locked = True`), `domain_scoring_status = 'degraded'`, `certification_domain_scores` rows exist with `source = 'degraded_estimate'` and `mastery_score ≤ 0.5`, and no exception propagates to the HTTP layer (returns 200).

**Definition of done:** both scenario tests green.  Manual test: comment out `ANTHROPIC_API_KEY` and set a dummy `NVIDIA_API_KEY`, hit the skill-assessments endpoint, confirm the profile locks and the response is 200 with degraded status.

---

### Step 14.4 — DB migration + ORM model for `domain_scoring_status`

**Goal:** add the `domain_scoring_status` column to `practitioner_profiles` in the database, update the ORM model, and tighten the `certification_domain_scores.source` check constraint to include `'degraded_estimate'`.

**Context to load:** `backend/alembic/versions/` (latest is `017`), `backend/app/db/models.py`.

**Build:**

1. **Migration `018_domain_scoring_status.py`**:
   - `ALTER TABLE practitioner_profiles ADD COLUMN domain_scoring_status TEXT NOT NULL DEFAULT 'pending'`
   - `ADD CONSTRAINT ck_domain_scoring_status CHECK (domain_scoring_status IN ('pending', 'lm_scored', 'degraded'))`
   - Drop and re-add the `ck_certification_domain_scores_source` constraint (if it exists) to add `'degraded_estimate'` as a valid value.
   - Run `alembic upgrade head` immediately.

2. **`PractitionerProfile` ORM model** — add:
   ```python
   domain_scoring_status: Mapped[str] = mapped_column(
       sa.String(50), nullable=False, server_default="pending", default="pending"
   )
   ```

3. **Expose in profile API response** — add `domain_scoring_status: str` to the profile schema returned by `GET /practitioners/{id}/profiles` and the `upsert_skill_assessments` response.

**Scenario tests:**
- *Migration is idempotent* — Given `alembic upgrade head` runs twice, the second run makes no changes.
- *Default is `pending`* — Given a profile created before Step 14.3 logic runs (i.e., before the Domain Scorer fires), `domain_scoring_status` defaults to `'pending'`.

**Definition of done:** migration applied locally; both scenario tests green; profile API response includes `domain_scoring_status`.

---

### Step 14.5 — Frontend `domain_scoring_status` awareness

**Goal:** the radar and domain gap chart communicate scoring quality to the practitioner.  Three states need distinct UI treatment:

| Status | Radar / Gap chart display |
|---|---|
| `lm_scored` | Normal — no badge |
| `degraded` | Amber badge: "⚠️ Scores estimated — take quizzes to refine" below the radar |
| `pending` | Grey badge: "Scoring in progress…" (should be very rare after Step 14.3) |

**Context to load:** `frontend/src/components/SkillRadar/SkillRadar.tsx`, `frontend/src/api/types.ts`.

**Build:**

1. **Update TypeScript profile type** — add `domain_scoring_status: 'pending' | 'lm_scored' | 'degraded'` to the `PractitionerProfile` interface in `frontend/src/api/types.ts`.

2. **`ScoringStatusBadge` component** — small inline component (can live at the bottom of `SkillRadar.tsx`):
   ```tsx
   function ScoringStatusBadge({ status }: { status: string }) {
     if (status === 'lm_scored') return null;
     if (status === 'degraded') return (
       <div style={{ color: '#b45309', fontSize: '0.8rem', marginTop: '0.5rem' }}>
         ⚠️ Scores estimated from self-assessment — take quizzes to refine
       </div>
     );
     return (
       <div style={{ color: '#6b7280', fontSize: '0.8rem', marginTop: '0.5rem' }}>
         ⏳ Scoring in progress…
       </div>
     );
   }
   ```

3. **Wire into `SkillRadar`** — pass `domain_scoring_status` from the profile data down to the radar and render `<ScoringStatusBadge />` below the `<DomainLegend />`.

4. **Domain gap chart** — same badge, placed below the chart if `domain_scoring_status !== 'lm_scored'`.

**Scenario tests:** none (frontend component — covered by visual inspection in the Definition of Done).

**Definition of done:** run the app locally with a degraded profile (created in Step 14.3's manual test), confirm the amber badge appears on both radar and domain gap chart.  `lm_scored` profiles show neither badge.

---

### Step 14.6 — Render env-var checklist & documentation freeze

**Goal:** every environment variable the production deployment needs is documented in one place, and the three affected docs are updated to reflect the Phase 14 architecture.

**Context to load:** `docs/MULTI_PROVIDER.md`, `docs/architecture.md`.

**Build (documentation only — no code):**

1. **`docs/MULTI_PROVIDER.md`** — add:
   - Fallback chain section explaining NVIDIA → Haiku → degraded.
   - `APP_ANTHROPIC_MODEL_ID` to the configuration reference table (default `claude-haiku-4-5-20251001`).
   - **Render production env-var checklist** — the specific variables that must be set in the Render dashboard before the first deploy:

   | Variable | Value | Notes |
   |---|---|---|
   | `APP_BRAIN_MODEL` | `NVIDIA` | Primary provider |
   | `NVIDIA_API_KEY` | `nvapi-...` | From NVIDIA NIM dashboard |
   | `NVIDIA_MODEL_ID` | `nvidia/nemotron-3-ultra-550b-a55b` | Or latest Nemotron Ultra |
   | `NVIDIA_BASE_URL` | `https://integrate.api.nvidia.com/v1` | Default; only override if endpoint changes |
   | `ANTHROPIC_API_KEY` | `sk-ant-...` | **Required for Haiku fallback** — without this, provider failure degrades directly to mechanical scores |
   | `APP_ANTHROPIC_MODEL_ID` | `claude-haiku-4-5-20251001` | Haiku only — do not change to Sonnet/Opus |
   | `DATABASE_URL` | (Supabase connection string) | |
   | `SECRET_KEY` | (random 32-byte hex) | |

2. **`docs/architecture.md`** — add §Provider Resilience section (see design in this doc).

3. **`docs/data-model.md`** — add `domain_scoring_status` to the `practitioner_profiles` table description.

4. **`docs/MULTI_PROVIDER.md`** — update verification checklist to include fallback scenarios.

**Definition of done:** all four docs updated.  No code changes.  Running `/doctor` (if available) or a manual review confirms no doc is out of sync with the implementation.

---

# Phase 15 — Three-Tier Provider Chain with Circuit Breaker

**Why this phase exists.**  Phase 14's two-tier chain (NVIDIA Ultra → Haiku) solved the "stuck spinner" problem but left two gaps.  First, a 45-second NVIDIA timeout makes interactive quiz answers painfully slow when Ultra is degraded.  Second, the chain has no memory — it pays the full timeout cost on *every* request even when NVIDIA has been continuously failing for minutes.  Phase 15 replaces the two-tier `FallbackModelClient` with a three-tier `MultiTierModelClient` and adds an in-memory circuit breaker that eliminates the repeated timeout cost during sustained outages.

**Model assignments:**

| Tier | Model | Purpose |
|---|---|---|
| Ultra | `nvidia/nemotron-3-ultra-550b-a55b` | Highest quality; tried first in NVIDIA-primary mode |
| Lightning | `nvidia/nemotron-3.5-lightning-30b-a3b` | Faster, lighter; fallback within NVIDIA estate |
| Haiku | `claude-haiku-4-5-20251001` | Cost-controlled Anthropic fallback; always Haiku, never Sonnet/Opus |

**Both NVIDIA models are free-tier endpoints** (no per-token cost) — using both is additive value, not additive cost.  Anthropic Haiku is billed; it is always the last resort.

**Preconditions:** Phase 14 Definition of Done is met.

---

### Step 15.1 — Three-tier `MultiTierModelClient`

**Goal:** replace `FallbackModelClient` (2 tiers) with `MultiTierModelClient` (3 tiers).  Each tier has its own timeout.  A tier's failure (timeout *or* any exception) immediately hands off to the next tier — no retry within a tier.

**Context to load:** `backend/app/agents/model_client.py`, `docs/MULTI_PROVIDER.md`.

**Call chain when `APP_BRAIN_MODEL=NVIDIA`:**

```
Tier 1 — NVIDIAModelClient(Ultra)       10 s timeout, 1 attempt
  ↓ any failure
Tier 2 — NVIDIAModelClient(Lightning)   20 s timeout, 1 attempt
  ↓ any failure
Tier 3 — AnthropicModelClient(Haiku)    20 s timeout, 1 attempt
  ↓ any failure
AllProvidersUnavailableError raised
```

**Max wall time (all fail):** 10 + 20 + 20 = 50 s.

**Build:**

1. **`MultiTierModelClient`** — new class in `model_client.py`; replaces `FallbackModelClient` entirely.  Accepts a `tiers: list[tuple[ModelClient, float]]` — each element is `(client, timeout_seconds)`.  `parse()` iterates the list: on success, sets `_last_model_used` and returns; on failure, logs a WARNING with the tier's model ID and the error, then tries the next tier; if all tiers exhaust, raises `AllProvidersUnavailableError(errors: list[Exception])`.

2. **`AllProvidersUnavailableError(RuntimeError)`** — replaces `ProviderUnavailableError`.  Carries `errors: list[Exception]` (one per tier that failed).  `ProviderUnavailableError` is kept as an alias for one release cycle to avoid breaking any catch sites.

3. **`Agent.effective_model`** — update to detect `MultiTierModelClient` the same way it currently detects `FallbackModelClient` (via `_last_model_used`).

4. **`create_model_client()` factory** — updated in Step 15.4.

**Scenario tests:**
- *Tier 1 succeeds* — `_last_model_used` = Ultra model ID; Tier 2 and 3 never called.
- *Tier 1 times out, Tier 2 succeeds* — Ultra WARNING logged; `_last_model_used` = Lightning ID.
- *Tier 1 and 2 fail, Tier 3 succeeds* — two WARNINGs logged; `_last_model_used` = Haiku ID.
- *All three fail* — `AllProvidersUnavailableError` raised with 3 errors.
- *Timeout is respected* — asyncio mock confirms each tier's `wait_for` uses the correct timeout.

**Definition of done:** 5 scenario tests green; `FallbackModelClient` is superseded (kept as stub for backward compat with existing tests until 15.4 cleans up).

---

### Step 15.2 — In-memory circuit breaker

**Goal:** after 5 consecutive failures on *both* NVIDIA tiers together, skip NVIDIA for a 2-minute cooldown window.  All calls in that window go straight to Haiku.  After the window expires the chain resets and tries Ultra first again.

**Context to load:** `backend/app/agents/model_client.py`.

**Design:**

```
NvidiaCircuitBreaker (module-level singleton in model_client.py)
├── consecutive_failures: int    — increments on each call where BOTH NVIDIA tiers fail
├── open_until: float | None     — time.monotonic() deadline; None = breaker closed
├── threshold: int               — default 5 (env: NVIDIA_CIRCUIT_BREAKER_THRESHOLD)
└── cooldown_seconds: float      — default 120 (env: NVIDIA_CIRCUIT_BREAKER_COOLDOWN_SECS)
```

**Integration with `MultiTierModelClient`:**

- On each `parse()` call, before iterating tiers, check if the circuit breaker is open (`open_until` is set and `time.monotonic() < open_until`).
- If open → skip NVIDIA tiers entirely; start at Haiku.  Log INFO: "NVIDIA circuit breaker open — routing directly to Haiku (resets at HH:MM:SS)."
- If closed → run the full chain as normal.
- After a call where tiers 1 *and* 2 both failed: `consecutive_failures += 1`.  If it reaches `threshold`, set `open_until = now + cooldown_seconds` and log WARNING: "NVIDIA circuit breaker tripped after N consecutive failures — entering 2-min cooldown."
- After a call where at least one NVIDIA tier succeeds: `consecutive_failures = 0`.
- When `open_until` is set and `time.monotonic() >= open_until`: reset `open_until = None`, `consecutive_failures = 0`, log INFO: "NVIDIA circuit breaker reset — resuming normal tier chain."

**Module-level singleton (not DB, not Redis):** the breaker lives in process memory.  It resets on server restart, which is acceptable — a restart is a deliberate intervention and usually resolves transient outages.  With `--reload` (dev), each file-change restart also resets it, which is correct.

**Scenario tests:**
- *4 consecutive NVIDIA failures → breaker stays closed.*
- *5th failure → breaker opens; next call skips to Haiku.*
- *NVIDIA succeeds on a call → counter resets to 0.*
- *After cooldown expires → next call retries Ultra first.*
- *Breaker open + Haiku succeeds → `_last_model_used` = Haiku; call logged normally.*

**Definition of done:** 5 scenario tests green; breaker state visible in INFO logs.

---

### Step 15.3 — Reversed chain for `APP_BRAIN_MODEL=ANTHROPIC`

**Goal:** when the operator sets `APP_BRAIN_MODEL=ANTHROPIC`, the chain is the mirror image — Haiku first, then NVIDIA Ultra, then NVIDIA Lightning.  Ultra is preferred over Lightning as the first NVIDIA fallback because it produces higher-quality output; Lightning is the last resort within the NVIDIA estate.  The same `MultiTierModelClient` is used; only the tier order passed by the factory changes.

**Call chain when `APP_BRAIN_MODEL=ANTHROPIC`:**

```
Tier 1 — AnthropicModelClient(Haiku)    10 s timeout, 1 attempt
  ↓ any failure
Tier 2 — NVIDIAModelClient(Ultra)       20 s timeout, 1 attempt
  ↓ any failure
Tier 3 — NVIDIAModelClient(Lightning)   20 s timeout, 1 attempt
  ↓ any failure
AllProvidersUnavailableError raised
```

**Circuit breaker in ANTHROPIC mode:** the same `NvidiaCircuitBreaker` is *not* active when `APP_BRAIN_MODEL=ANTHROPIC` — NVIDIA is already the fallback, not the primary, and its failures don't justify skipping it (only its success is a bonus).  The circuit breaker only protects the NVIDIA-primary path.

**Scenario tests:**
- *ANTHROPIC mode, Haiku succeeds* — Tier 2 and 3 never called; `_last_model_used` = Haiku.
- *ANTHROPIC mode, Haiku fails, Ultra succeeds* — Haiku WARNING; `_last_model_used` = Ultra.
- *ANTHROPIC mode, all fail* — `AllProvidersUnavailableError`.

**Definition of done:** 3 scenario tests green; factory produces correct tier order.

---

### Step 15.4 — `.env` + config update

**Goal:** replace the single `NVIDIA_MODEL_ID` env var with `NVIDIA_MODEL_ID_PRIMARY` and `NVIDIA_MODEL_ID_SECONDARY`.  Add per-tier timeout vars and circuit-breaker threshold/cooldown vars.  Update `config.py`, `create_model_client()`, `.env`, and Render checklist.

**Context to load:** `backend/app/config.py`, `backend/app/agents/model_client.py`, `docs/MULTI_PROVIDER.md`.

**New env vars:**

| Variable | Default | Description |
|---|---|---|
| `NVIDIA_MODEL_ID_PRIMARY` | `nvidia/nemotron-3-ultra-550b-a55b` | Tier 1 NVIDIA model (Ultra) |
| `NVIDIA_MODEL_ID_SECONDARY` | `nvidia/nemotron-3.5-lightning-30b-a3b` | Tier 2 NVIDIA model (Lightning) |
| `NVIDIA_TIER1_TIMEOUT_SECS` | `10` | Hard timeout for Ultra (or Haiku in ANTHROPIC mode) |
| `NVIDIA_TIER2_TIMEOUT_SECS` | `20` | Hard timeout for Lightning |
| `ANTHROPIC_TIER_TIMEOUT_SECS` | `20` | Hard timeout for Haiku (any position in chain) |
| `NVIDIA_CIRCUIT_BREAKER_THRESHOLD` | `5` | Consecutive NVIDIA-only failures before cooldown |
| `NVIDIA_CIRCUIT_BREAKER_COOLDOWN_SECS` | `120` | Cooldown duration in seconds |

**Deprecate:** `NVIDIA_MODEL_ID` is removed.  Any `.env` that still has it should migrate to `NVIDIA_MODEL_ID_PRIMARY`.

**Build:**
1. Add fields to `Settings` in `config.py`.
2. Update `create_model_client()` to build `MultiTierModelClient` with the correct tier list and timeouts for both `NVIDIA` and `ANTHROPIC` modes.
3. Update `.env` (project root) with the new variable names.
4. Update `docs/MULTI_PROVIDER.md` Render checklist (Step 15.6).

**Scenario tests:**
- *Settings load all new vars with defaults.* — validates `Settings()` with no env overrides.
- *Factory produces 3-tier NVIDIA chain.* — tier order and timeouts match config.
- *Factory produces 3-tier ANTHROPIC chain.* — Haiku first, then Ultra, then Lightning.

**Definition of done:** 3 scenario tests green; `.env` updated; no references to `NVIDIA_MODEL_ID` (singular) remain in code or config.

---

### Step 15.5 — Graceful degraded response when all tiers fail

**Goal:** when `AllProvidersUnavailableError` reaches an endpoint, return HTTP 503 with a structured, human-readable error body rather than a 500.  The body tells the practitioner what happened and what to do.

**Context to load:** `backend/app/api/routes/profiles.py`, `backend/app/main.py`.

**Build:**

1. **Global exception handler** in `main.py` — catch `AllProvidersUnavailableError` (alongside the existing `RequestValidationError` handler); return:
   ```json
   {
     "error": "all_providers_unavailable",
     "message": "Our AI services are temporarily unavailable. Your progress is saved — please try again in a few minutes.",
     "retry_after_seconds": 120
   }
   ```
   HTTP 503 with `Retry-After: 120` header.

2. **Profile lock endpoint** — already catches `ProviderUnavailableError` (now `AllProvidersUnavailableError`) for domain scoring.  Keep the mechanical degraded-scoring fallback for that specific call; the 503 handler is for all *other* endpoints where there is no mechanical fallback (grader, quiz batch generator, etc.).

3. **Frontend** — add a global API error handler that detects `error: "all_providers_unavailable"` from any API call and shows a toast/banner: "⏳ AI services are temporarily busy — please retry in a moment." with a Retry button.

**Scenario tests:**
- *`AllProvidersUnavailableError` from grader → 503 with correct body.*
- *`AllProvidersUnavailableError` from quiz batch → 503.*
- *`AllProvidersUnavailableError` from domain scorer → 200 with degraded scores (mechanical fallback still wins for this specific path).*

**Definition of done:** 3 scenario tests green; manual test confirms the toast appears in the frontend when all providers are stubbed to fail.

---

### Step 15.6 — Documentation freeze

**Goal:** update `docs/MULTI_PROVIDER.md` and `docs/architecture.md` to reflect the Phase 15 architecture.  No code changes.

**Context to load:** `docs/MULTI_PROVIDER.md`, `docs/architecture.md`.

**Build (documentation only):**

1. **`docs/MULTI_PROVIDER.md`** — replace the Phase 14 "Fallback Chain" section with the Phase 15 three-tier chain diagram; update the config reference table with all new env vars; update the Render checklist; add Circuit Breaker behaviour section.

2. **`docs/architecture.md`** — update §Provider Resilience to describe `MultiTierModelClient`, the three-tier chain, and the circuit breaker.

**Definition of done:** both docs match the implementation.  Running the scenario tests from Steps 15.1–15.5 confirms no doc is out of sync.

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

> ⚠️ **Superseded by Phase 9.1.** This agent and the `rollups` table are removed in Step 9.1. The code exists in the repo but is no longer part of the active product. Do not extend this agent; do not add new routes that depend on it.

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

> ⚠️ **Superseded by Phase 9.1.** The fully-automated nightly nudge + rollup pipeline is removed in Step 9.1. Correlation snapshots (Step 3.2) still exist and feed the admin-driven nudge campaign system (Phase 7), but there is no longer a scheduled nightly run that auto-generates nudges or rollups.

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

> ⚠️ **Superseded by Phase 9.1.** The rollup view is removed in Step 9.1. Leadership users no longer have a rollup dashboard. The `RollupView` component and its route are deleted as part of that step.

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

> ⚠️ **Modified by Phase 9.3 & 9.4.** After this step's skill-assessment save succeeds, the profile is permanently locked (Step 9.3). Additionally, the saved skill ratings are no longer piped into the Skill Profiler for radar computation (Step 9.4) — they are captured as part of the profile record but the Skill Radar is driven solely by quiz answers going forward.

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

> ⚠️ **Modified by Phase 9.3.** The "Edit" action on profile cards is replaced with a read-only "View" action in Step 9.3. Once a profile is locked (saved through the full wizard), it cannot be edited — only deleted or viewed. Creating a new profile is the only path to changing certification or questionnaire answers.

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

> ⚠️ **Modified by Phase 9.4.** The Skill Radar's mastery scores are driven exclusively by quiz answers after Step 9.4. Self-assessment signals from the profile are no longer reflected in the radar. A new empty-state message should explain this: "Take quizzes to see your skill levels populate." The guidance messages (< 40%, 40–69%, etc.) remain but are now entirely based on quiz-derived mastery.

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

> ⚠️ **Extended by Phase 9.5 & 9.6.** The quiz question ordering established here is extended in Steps 9.5–9.6: mastery now follows a progressive round-based scoring ceiling, and exhausted question sets are automatically refreshed with a new generation of items.

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

---

# Phase 7 — Smart Nudge System

This phase replaces the automated, nightly-pulse-only nudge flow with an admin-driven, intent-based campaign system. The central idea: an Admin or Leadership member can see a **Nudges** menu (hidden from practitioners), use LLM to generate contextual nudge categories from aggregate KPI data, select matching practitioners, review and edit a composed message, and send it. Practitioners receive nudges both in-app (as unread messages on their Adoption Trends tab) and via email. A progress trend chart on the same tab shows mastery trajectory over time.

---

### Step 7.1 — Nudge data model expansion & API

**Goal:** extend the data model to support admin-driven nudge campaigns with category tracking, in-app read/unread state, and historical mastery snapshots for trend charts.

**Preconditions:** 6.8 (app is fully operational).
**Context to load:** `docs/data-model.md`, `docs/architecture.md`.

**Build:**

*New migration:*
- `nudge_categories`: `id` (UUID PK), `description` (text — human-readable, e.g. "Practitioners who haven't taken quizzes in 7 days"), `criteria` (jsonb — machine-readable filter params such as `{"no_quiz_days_gte": 7}`), `is_custom` (boolean — `true` when the admin typed it manually), `created_by_admin_id` (FK → `admin_users`), `created_at`.
- `mastery_history`: `id` (UUID PK), `practitioner_id` (FK → `practitioners`), `skill_id` (FK → `skills`), `mastery_score` (float 0–1), `recorded_at` (timestamp). Append-only: a row is added here every time the Skill Profiler upserts `skill_profile_snapshots`. No unique constraint — multiple rows per (practitioner, skill) are expected. Retain only 90 days of history per practitioner.
- Expand `nudges`: add `nudge_category_id` (nullable FK → `nudge_categories`), `subject` (nullable text — email subject line), `is_read` (boolean, default false), `read_at` (nullable timestamp), `created_by_admin_id` (nullable FK → `admin_users` — set for campaign nudges, null for nightly-pulse nudges).

*API routes:*
- `POST /nudges/categories` — create a category (used by both the LLM agent and the custom-input path).
- `GET /nudges/categories` — list recent categories (admin/leadership).
- `POST /nudges/categories/{id}/preview-recipients` — resolve which practitioners match a category's criteria; returns `[{id, name, email, action_profile_summary}]`.
- `POST /nudges/categories/{id}/compose` — run the Nudge Composer Agent for this category; returns `{subject, body, tone_check, recipients}`. Does not yet create nudge rows — this is the preview step.
- `POST /nudges/send` — given `{category_id, message_subject, message_body, recipient_overrides: [{practitioner_id, include: bool}]}`, create one `nudges` row per included practitioner (status `sent`, `sent_at` = now), then trigger email delivery (wired in Step 7.6 — stub for now).
- `GET /nudges/sent` — list sent campaigns (readonly, admin/leadership).
- `GET /practitioners/{id}/nudges` — list a practitioner's nudges, unread first; requires `require_practitioner` + self-only enforcement.
- `PATCH /nudges/{id}/read` — mark a nudge as read; only the recipient practitioner may call this.
- `GET /practitioners/{id}/mastery-history` — return time-series rows from `mastery_history`, filtered by optional `skill_id` and `days` query params.

**Scenario tests:**
- *A nudge created for a practitioner starts with `is_read = false`.*
- *Calling `PATCH /nudges/{id}/read` sets `is_read = true` and populates `read_at`.*
- *`preview-recipients` for a `no_quiz_days_gte: 7` category returns only practitioners with zero attempts in the last 7 days, not all practitioners.*

**Definition of done:** all three pass; migration runs clean against local DB.

---

### Step 7.2 — Nudge Category Generator Agent 👤

**Goal:** a new LLM agent that ingests aggregate KPI data (no PII — only counts, averages, and gap summaries) and proposes up to 10 actionable nudge categories, each with machine-readable criteria and a tone hint for the Nudge Composer.

**Preconditions:** 7.1.
**Context to load:** `docs/architecture.md`, `docs/human-in-the-loop.md`.

**Build:**
- `backend/app/agents/nudge_category_generator.py` + `agents/prompts/nudge_category_generator.md` — 👤 write the prompt yourself (see below).
- `NudgeCategoryInput` (aggregate-only — no practitioner names or emails):
  - `total_practitioners`: int
  - `practitioners_no_quiz_7d`: int
  - `practitioners_no_quiz_14d`: int
  - `practitioners_no_profile`: int
  - `practitioners_profile_unrated`: int (active profile but zero skill assessments saved)
  - `skill_gap_summary`: list of `{skill_name, avg_gap_score, practitioner_count}` (top 5 by gap)
  - `practitioners_stalled`: int (mastery unchanged in 14+ days)
  - `practitioners_near_cert_ready`: int (cert-relevant mastery avg ≥ 80 %)
  - `nudges_sent_last_7d`: int
- `NudgeCategoryOutput`: `categories: list[NudgeCategory]` (max 10), each with:
  - `title`: str (short label, e.g. "Idle for 7+ days")
  - `description`: str (one sentence explaining who qualifies)
  - `criteria`: dict (machine-readable, e.g. `{"no_quiz_days_gte": 7}`)
  - `estimated_reach`: int
  - `tone_hint`: str (one-line tone guidance, e.g. "warm re-engagement, not scolding")
- `GET /nudges/generate-categories` API route: queries aggregate stats, runs the agent, persists suggested categories to `nudge_categories`, returns the list.
- Recipient resolver: a pure Python function `resolve_recipients(criteria: dict) → list[Practitioner]` that translates criteria keys to DB queries. Supported keys:
  - `no_quiz_days_gte: N` — no attempts in last N days
  - `no_profile: true` — no active profile
  - `profile_unrated: true` — active profile but no skill assessments
  - `mastery_stalled_days_gte: N` — no mastery improvement in last N days
  - `skill_gap_skill_id: UUID` — gap_score ≥ 0.5 on this skill
  - `near_cert_ready: true` — cert-relevant mastery avg ≥ 80 %
  - `custom_description: str` — free-text; resolver returns all practitioners and marks the row for manual review in the UI

**Scenario tests:**
- *A dataset with 8 practitioners having no quizzes in 7 days generates at least one category with `estimated_reach` near 8.*
- *The resolver for `{"no_quiz_days_gte": 7}` returns only qualifying practitioners, not all practitioners.*
- *A custom-description category creates a `nudge_categories` row with `is_custom = true` and `criteria.custom_description` populated.*

**Definition of done:** all three pass against the stub Claude client.

> 👤 **Human-in-the-loop:** write `agents/prompts/nudge_category_generator.md` yourself before implementing. The categories it generates determine who gets nudged — a category that flags ordinary behavior (e.g. "practitioners who skip weekends") or sets a punishing tone will erode trust. Own the criteria boundaries and the `tone_hint` vocabulary. See `docs/human-in-the-loop.md`.

---

### Step 7.3 — Nudge Campaign workflow (recipient resolution + composition)

**Goal:** wire the NudgeCategoryGenerator output into a composable campaign: given a selected category, resolve recipients and generate an encouraging nudge message via the Nudge Composer Agent — returning a full preview before anything is sent.

**Preconditions:** 7.2.
**Context to load:** `docs/architecture.md`.

**Build:**
- Extend the existing `Nudge Composer Agent` input to accept `NudgeCampaignInput` — category description, `tone_hint` from the category, and matched-recipient count (not names). Output adds `subject: str` and `tone_check: str` (one-sentence self-assessment: "Is this message encouraging rather than punishing?").
- `POST /nudges/categories/{id}/compose` calls `resolve_recipients(category.criteria)`, runs the Nudge Composer Agent, and returns `{subject, body, tone_check, recipients: [{id, name, email, action_profile_summary, include: true}]}`. No DB writes at this stage — preview only.
- `POST /nudges/send` creates one `nudges` row per practitioner where `include = true` (status `sent`, `sent_at` = now), writes a `workflow_runs` row under `nudge_campaign`, then calls the email stub from Step 7.6.

**Scenario tests:**
- *Composing a campaign for a "no quiz in 7 days" category returns a `body` containing none of the words "failed", "missing", "behind", "overdue", or "lacking".*
- *The `recipients` list from `/compose` matches what `resolve_recipients` returns for the same criteria.*
- *Calling `/send` with two practitioners' `include` set to `false` creates nudge rows for the remaining practitioners only — the excluded two have no new nudge rows.*

**Definition of done:** all three pass.

---

### Step 7.4 — Admin/Leadership Nudge Management UI

**Goal:** the full admin-side nudge campaign experience — generate categories, pick or write one, review matching practitioners, edit the message, and send.

**Preconditions:** 7.3.
**Context to load:** `docs/architecture.md` (Auth §What each role can see).

**Build:**
- New page `frontend/src/pages/NudgesPage.tsx`, routed at `/nudges`. Route guard: Admin and Leadership sessions only — practitioner sessions are redirected away. Top-nav "Nudges" link is rendered only for Admin/Leadership sessions (hidden entirely for practitioners).
- **Section 1 — Generate categories**: a "Generate Nudge Categories" primary button calls `GET /nudges/generate-categories`. Shows a spinner while generating. Renders up to 10 category cards, each with: title, description, estimated_reach badge, and a "Select" button.
- **Section 2 — Custom category**: a text box ("Describe your own category in plain English") + "Apply" button. On submit, creates a `nudge_categories` row (`is_custom = true`) and immediately loads recipients.
- **Section 3 — Recipient table** (shown after any category is selected): columns: Name, Email, Action Profile (cert goal + active profile name as one line), Include (checkbox, default checked). "Select all / Deselect all" toggle. A live count chip: "N practitioners selected".
- **Section 4 — Nudge message**: Subject (single-line) and Body (multiline) auto-filled from `/compose`. Both freely editable. "(↻ Regenerate message)" link re-calls the compose endpoint. `tone_check` shown as small italic note below the body.
- **Section 5 — Send**: "Send nudge to N practitioners" button. Confirm dialog. On confirm → `POST /nudges/send` → success banner + readonly table of just-sent records (Name, Email, Sent at).
- **Sent history panel**: collapsible "Previous nudge campaigns" section showing the last 20 campaigns from `GET /nudges/sent`.
- **Leadership restriction**: Leadership role sees the Nudges menu and the sent history panel in read-only mode. Sections 1–5 interactive controls are disabled with an "Admins only" tooltip.

**Scenario tests (Playwright):**
- *An admin can generate categories, select one, see matching practitioners, and successfully send — the sent-history panel shows the new campaign.*
- *A leadership user can navigate to `/nudges` and see the sent history panel but the "Generate Nudge Categories" button is disabled.*
- *Unchecking one practitioner before sending excludes them — the sent-history count is one less than the total shown in the table.*

**Definition of done:** all three pass.

---

### Step 7.5 — Practitioner Nudge Inbox & Progress Trend Chart

**Goal:** practitioners see received nudges as unread/read messages on their Adoption Trends tab, plus a mastery progress trend chart.

**Preconditions:** 7.4.

**Build:**

*Nudge Inbox panel* on the Adoption Trends tab:
- A "Messages" section listing the practitioner's nudges from `GET /practitioners/{id}/nudges`, newest first. Unread nudges show a blue dot and bold subject. Clicking expands the full body and calls `PATCH /nudges/{id}/read` (optimistic update — dot disappears immediately).
- A "Messages (N unread)" badge on the Adoption Trends tab label in the top nav, driven by a `useUnreadNudgeCount` polling hook (60 s interval). Hidden when N = 0.

*Progress Trend Chart* (new `ProgressTrendChart` component):
- Data: `GET /practitioners/{id}/mastery-history` with optional `skill_id` and `days` params.
- Default: aggregate average mastery across all skills, last 30 days.
- Skill selector dropdown + "30 days / 90 days" toggle.
- Uses the same Recharts setup and color palette as the Skill Radar.
- Empty state (fewer than 2 data points): "Keep going — your progress chart fills in as you complete quizzes and update your profile."

*Skill Profiler integration:* update `backend/app/agents/skill_profiler.py` to append to `mastery_history` whenever it upserts `skill_profile_snapshots`.

**Scenario tests (Playwright):**
- *A practitioner with one unread nudge sees a "1 unread" badge on the Adoption Trends tab.*
- *Clicking the nudge card marks it read — the badge disappears and the card loses its bold styling.*
- *A practitioner with at least two mastery-history data points on skill X sees a non-empty trend line when they select that skill from the dropdown.*

**Definition of done:** all three pass.

---

### Step 7.6 — Email delivery integration

**Goal:** when nudges are sent, practitioners also receive an email to their registered address.

**Preconditions:** 7.5.

**Build:**
- `backend/app/services/email.py` — async email service wrapping `aiosmtplib`. Config via `.env`: `SMTP_HOST`, `SMTP_PORT` (default 587), `SMTP_FROM`, `SMTP_USER` (optional), `SMTP_PASSWORD` (optional). If `SMTP_HOST` is not set, log a warning and skip delivery silently.
- HTML email: subject from `nudges.subject`, body from `nudges.content` in a clean single-column layout, signed "— The Mastery Pulse Team". Footer: "You're receiving this because you're a registered practitioner in Mastery Pulse."
- `POST /nudges/send` calls the email service after writing DB rows. Email failures are logged but do not roll back the DB write.
- `.env.example` updated with the four SMTP config keys.

**Scenario tests:**
- *Sending a nudge when `SMTP_HOST` is not configured logs a warning and returns a 200 without raising an exception.*
- *Given a mock SMTP stub, sending to three practitioners delivers exactly three emails — one per recipient.*

**Definition of done:** both pass; `.env.example` updated.

---

### Step 7.7 — End-to-end Nudge Playwright suite

**Goal:** string together the full admin-initiates-nudge → practitioner-receives-nudge journey end-to-end.

**Preconditions:** 7.6.
**Build:** `tests/scenarios/nudge-journey.spec.ts`

**Scenario tests:**
- *Full nudge journey*: admin logs in → navigates to Nudges → clicks "Generate Nudge Categories" → selects a category → sees matching practitioners in the table → message is auto-filled → sends → practitioner logs in → sees "1 unread" badge on Adoption Trends → clicks the nudge → badge disappears.
- *Custom category journey*: admin types a custom description → practitioners appear in the table → admin sends → history panel shows the new campaign with the correct recipient count.

**Definition of done:** both journeys pass against a full local stack (local Postgres + seeded data).

---

# Phase 8 — Multi-Model Provider Support (NVIDIA Nemotron)

This phase adds support for NVIDIA's Nemotron 3 Ultra model as an alternative LLM provider alongside Anthropic Claude. The system uses an environment variable `APP_BRAIN_MODEL` to select the provider at runtime, with full backward compatibility for existing Anthropic-based deployments. The agent framework, MCP servers, prompts, and architecture remain unchanged — only the model client layer is abstracted.

---

### Step 8.1 — Configuration & model abstraction layer

**Goal:** Introduce a unified model abstraction layer that allows switching between Anthropic and NVIDIA providers via configuration, without changing agent code.

**Preconditions:** 7.7 (all existing functionality operational).
**Context to load:** `docs/architecture.md`, `docs/coding-guidelines.md`, `backend/app/agents/base.py`.

**Build:**

*Configuration (`.env` and `backend/app/config.py`):*
- Add `APP_BRAIN_MODEL` env var with values: `ANTHROPIC` (default) | `NVIDIA`
- Add `NVIDIA_API_KEY` env var (required when `APP_BRAIN_MODEL=NVIDIA`)
- Add `NVIDIA_BASE_URL` env var (default: `https://integrate.api.nvidia.com/v1`)
- Add `NVIDIA_MODEL_ID` env var (default: `nvidia/nemotron-3-ultra-550b-a55b`)
- Update `Settings` class in `config.py` with these new fields

*Abstraction layer (`backend/app/agents/model_client.py` — new file):*
- Define a `ModelClient` protocol extending the existing `ClaudeClient` protocol from `base.py`
- Create `AnthropicModelClient` wrapper around `anthropic.AsyncAnthropic` (current behavior)
- Create `NVIDIAModelClient` wrapper using OpenAI-compatible SDK (NVIDIA API is OpenAI-compatible)
- Both implementations must support the `messages.parse()` method with Structured Outputs
- Factory function `create_model_client(settings) -> ModelClient` that reads `APP_BRAIN_MODEL` and returns the appropriate client

*Agent base class update (`backend/app/agents/base.py`):*
- Change `ClaudeClient` type hint to `ModelClient` protocol
- Update `_call_claude` to use the new protocol methods
- Ensure retry logic, token counting, and error handling work identically for both providers
- The `Agent` class constructor should accept `ModelClient` (already does via protocol)

**Scenario tests:**
- Given `APP_BRAIN_MODEL=ANTHROPIC`, `create_model_client` returns `AnthropicModelClient` that works with existing tests
- Given `APP_BRAIN_MODEL=NVIDIA` with valid API key, `create_model_client` returns `NVIDIAModelClient`
- Both clients correctly handle Structured Outputs parsing for a simple agent output schema
- Both clients return token usage and latency in the same format
- Transient errors (rate limits, timeouts) are correctly identified and retried for both providers

**Definition of done:** All scenario tests pass; existing agent tests still pass with `APP_BRAIN_MODEL=ANTHROPIC`.

---

### Step 8.2 — NVIDIA Nemotron client implementation

**Goal:** Implement the NVIDIA Nemotron client with full feature parity to the Anthropic client for the agent use case.

**Preconditions:** 8.1.
**Context to load:** NVIDIA API documentation (OpenAI-compatible), `backend/app/agents/model_client.py`.

**Build:**

*Client implementation (`backend/app/agents/model_client.py` — extend):*
- Use `openai.AsyncOpenAI` with `base_url` set to NVIDIA endpoint and API key
- NVIDIA Nemotron supports Structured Outputs via `response_format` parameter (JSON Schema)
- Implement `messages.parse()` equivalent using OpenAI's `beta.chat.completions.parse()` 
- Handle NVIDIA-specific response format differences (e.g., token usage field names)
- Map NVIDIA model IDs to internal agent model strings (e.g., `nvidia/nemotron-3-ultra-550b-a55b`)

*Token counting & observability:*
- NVIDIA returns `usage.prompt_tokens` and `usage.completion_tokens` (OpenAI format)
- Ensure `AgentRun` persistence receives correct token counts for cost tracking
- Latency measurement must work identically

*Error handling:*
- Map NVIDIA error codes to the existing `_transient_errors` tuple
- Rate limits (429), timeouts, connection errors, 5xx should all trigger retries
- Non-transient errors (400, 401, 404) should fail fast

**Scenario tests:**
- NVIDIA client successfully calls Nemotron with a simple prompt and returns parsed output
- Structured Outputs validation works — malformed responses are caught and raise `ValidationError`
- Token counts are correctly extracted and match NVIDIA API response
- Transient errors trigger retry with exponential backoff
- Non-transient errors fail immediately without retry
- Works with the stub client fixture pattern (test double)

**Definition of done:** All scenario tests pass; client can be used as a drop-in replacement in agent tests.

---

### Step 8.3 — Agent framework integration

**Goal:** Wire the model abstraction into all nine agents and workflows, ensuring each agent can use either provider seamlessly.

**Preconditions:** 8.2.
**Context to load:** `docs/architecture.md` (Model selection table), `backend/app/agents/*.py`, `backend/app/workflows/*.py`.

**Build:**

*Agent model configuration:*
- Update `docs/architecture.md` Model Selection table to include NVIDIA model mappings
- Each agent's `model` class attribute becomes a *default* for Anthropic; NVIDIA uses its own model ID
- Add optional `model_override` parameter to `Agent.__init__` for per-instance model selection
- Agent factories in workflows should use `create_model_client(settings)` and pass to agents

*Workflow integration:*
- Update `generate_learning_path.py`, `nightly_pulse.py`, `nudge_campaign.py` to use `create_model_client`
- `certification_advisor` route, `learning_paths/generate` route, `attempts` route all need to create client via factory
- Message Batches API note: NVIDIA doesn't support batch API — document this limitation; nightly pulse falls back to synchronous

*MCP server compatibility:*
- MCP servers use `anthropic[mcp]` client-side pattern which is Anthropic-specific
- For NVIDIA: MCP tools must be called via the agent's model (not via Anthropic's tool runner)
- Option A: Disable MCP for NVIDIA (agents use only built-in knowledge)
- Option B: Implement a generic tool-calling loop in the agent base class
- **Decision:** Option A for v1 — MCP servers only available with Anthropic provider; document clearly

**Scenario tests:**
- All 9 agents work with `APP_BRAIN_MODEL=ANTHROPIC` (regression)
- All 9 agents work with `APP_BRAIN_MODEL=NVIDIA` (new functionality)
- Workflows complete end-to-end with both providers
- Agent output schemas validate correctly for both providers
- `agent_runs` rows correctly record `model_used` for both providers
- MCP-dependent agents (Skill Profiler, Usage-Signal) work with Anthropic; with NVIDIA they skip MCP and use prompt-only context (graceful degradation)

**Definition of done:** All scenario tests pass; full regression suite green for both providers.

---

### Step 8.4 — MCP server compatibility

**Goal:** Document and implement MCP server behavior for NVIDIA provider (graceful degradation).

**Preconditions:** 8.3.
**Context to load:** `docs/architecture.md` (MCP strategy section), `backend/app/mcp_servers/*.py`.

**Build:**

*Documentation updates:*
- Add section to `docs/architecture.md` explaining MCP is Anthropic-only in v1
- When `APP_BRAIN_MODEL=NVIDIA`, agents that use MCP log a warning and proceed without external data
- Certification Advisor: catalog still passed in prompt (no MCP needed)
- Skill Profiler: `mcp-learning-portal` data omitted; works with only `skill_profile_events`
- Usage-Signal: `mcp-usage-signals` data omitted; works with empty raw signals (produces no usage events)

*Implementation:*
- Add `has_mcp` flag to agent input schemas where MCP is used
- In workflow, conditionally fetch MCP data only when using Anthropic provider
- Pass `portal_certifications=None` etc. to Skill Profiler when NVIDIA

**Scenario tests:**
- Skill Profiler with NVIDIA runs without MCP data and produces valid snapshots
- Usage-Signal with NVIDIA runs with empty raw signals and produces empty normalized events (no crash)
- Workflow logs clear warning when MCP is skipped due to provider

**Definition of done:** All scenario tests pass; behavior documented.

---

### Step 8.5 — Testing & validation

**Goal:** Comprehensive test coverage for dual-provider support, including live API tests and CI integration.

**Preconditions:** 8.4.
**Context to load:** `docs/coding-guidelines.md` (Testing section), `backend/tests/conftest.py`.

**Build:**

*Stub client updates:*
- Update `backend/tests/fixtures/stub_claude_client.py` to support both provider response formats
- Add `StubNVIDIAModelClient` fixture for NVIDIA-specific testing
- Ensure existing `StubClaudeClient` still works for Anthropic tests

*Test matrix:*
- Add `@pytest.mark.provider_anthropic` and `@pytest.mark.provider_nvidia` markers
- Run full scenario suite twice in CI (or sequentially): once with `APP_BRAIN_MODEL=ANTHROPIC`, once with `APP_BRAIN_MODEL=NVIDIA` (if NVIDIA_API_KEY available)
- If NVIDIA_API_KEY not set in CI, skip NVIDIA tests with clear message

*Live tests:*
- Add `@pytest.mark.live` tests for NVIDIA provider (manual/scheduled)
- Validate prompt quality with Nemotron — some prompts may need tuning for Nemotron's style
- Document any prompt adjustments needed per agent

*Observability:*
- Verify `agent_runs.model_used` correctly records `nvidia/nemotron-3-ultra-550b-a55b` for NVIDIA runs
- Cost tracking works (token counts from NVIDIA API)

**Scenario tests:**
- All existing scenario tests pass with both providers (where MCP is not required)
- New NVIDIA-specific scenario tests pass
- CI runs both provider test suites
- Observability dashboard shows correct model names for both providers

**Definition of done:** All scenario tests pass for both providers; CI configured.

---

### Step 8.6 — Documentation & migration guide

**Goal:** Complete documentation for dual-provider support, including migration guide and architecture updates.

**Preconditions:** 8.5.
**Context to load:** All docs files.

**Build:**

*Architecture updates (`docs/architecture.md`):*
- Add "Multi-Model Provider Support" section
- Update Model Selection table with NVIDIA mappings
- Add MCP compatibility note
- Add configuration reference for `APP_BRAIN_MODEL`, `NVIDIA_API_KEY`, `NVIDIA_BASE_URL`, `NVIDIA_MODEL_ID`

*Coding guidelines updates (`docs/coding-guidelines.md`):*
- Add section on model-agnostic agent development
- Note: agents must not assume Anthropic-specific features (MCP, specific error types)

*Configuration reference (`.env.example`):*
- Add all new env vars with comments

*Migration guide (`docs/MULTI_PROVIDER.md` — new file):*
- How to switch providers
- Known limitations (MCP, Message Batches API)
- Prompt tuning tips for Nemotron
- Troubleshooting common issues

*CLAUDE.md updates:*
- Add Phase 8 to step index
- Note the new model abstraction layer

**Scenario tests:**
- Documentation renders correctly
- `.env.example` includes all required variables
- Migration guide is complete and accurate

**Definition of done:** All documentation updated; migration guide created; new team member can switch providers following the guide.

---

## Additional Test Cases for Phase 8

The following test scenarios must be added/modified across the test suite:

1. **Model Client Factory Tests** (`tests/scenarios/test_model_client.py` — new):
   - Factory returns correct client type based on `APP_BRAIN_MODEL`
   - Both clients implement `ModelClient` protocol
   - Invalid `APP_BRAIN_MODEL` value raises clear error

2. **NVIDIA Client Tests** (`tests/scenarios/test_nvidia_client.py` — new):
   - Structured Outputs parsing with Nemotron
   - Token counting accuracy
   - Error mapping and retry behavior
   - Works with stub fixture

3. **Agent Regression Tests** (modify existing):
   - Each agent test class runs twice: once with Anthropic stub, once with NVIDIA stub
   - Use `@pytest.mark.parametrize("provider", ["anthropic", "nvidia"])`
   - MCP-dependent agents skip MCP data when provider=NVIDIA

4. **Workflow Integration Tests** (modify existing):
   - `test_generate_learning_path` runs with both providers
   - `test_nightly_pulse` runs with both providers (NVIDIA skips Message Batches API)
   - MCP-dependent workflows log warnings with NVIDIA

5. **Configuration Tests** (`tests/scenarios/test_config.py` — extend):
   - Settings loads all new env vars correctly
   - Default values are sensible
   - Missing NVIDIA_API_KEY raises error when NVIDIA provider selected

6. **Observability Tests** (extend existing):
   - `agent_runs.model_used` records correct model string for NVIDIA
   - Token counts match API response for both providers

7. **Frontend Tests** (no changes needed):
   - Frontend is provider-agnostic; no test modifications required

---

# Phase 9 — Mastery Refinements: Quiz-Driven Radar, Profile Lockdown & Admin Simplification

This phase tightens the product around three principles:
1. **Profile immutability** — a submitted profile is a permanent record; to change course, create a new one.
2. **Quiz-first mastery** — the Skill Radar reflects only what the practitioner has demonstrated through answers, not what they claimed in a self-assessment.
3. **Focused admin view** — when leadership or admins look at a practitioner, they see one thing: the Skill Radar.
4. **Leaner signal loop** — the automated nightly nudge pipeline and leadership rollup reports are removed; the admin campaign nudge system (Phase 7) remains.

> **Steps 9.1–9.4 are complete.** The remaining items originally scoped here — progressive scoring (was 9.5), auto-refresh (was 9.6), and visual trend indicators (was 9.7) — have been absorbed into **Phase 10**, where the certification-domain alignment foundation must be in place first. See Phase 10 for the full implementation sequence.

---

### Step 9.1 — Remove Rollups & nightly auto-nudge pipeline

**Goal:** strip out the two pieces of functionality the product no longer needs: aggregated leadership rollup reports and the fully-automated nightly nudge generation. The admin-driven nudge campaign system (Phase 7) stays intact; only the autopilot path is removed.

**Preconditions:** 8.6 (all existing functionality operational).
**Context to load:** `docs/architecture.md` (Agent inventory + Nightly Pulse sections), `docs/data-model.md` (rollups table).

**Build:**

*Backend:*
- Archive `backend/app/agents/rollup_reporter.py` and `prompts/rollup_reporter.md` (move to `backend/app/agents/_deprecated/` so the history is clear).
- Write and apply a migration that drops the `rollups` table. Verify no FK constraints from other tables point to it.
- Archive or stub `backend/app/workflows/nightly_pulse.py` — replace its body with a single `raise NotImplementedError("nightly_pulse removed in Phase 9.1")` so any accidental trigger surfaces clearly rather than silently doing nothing.
- Remove all API routes that served rollup data (`GET /rollups/`, any rollup-scoped endpoints in `api/routes/`).
- Update `workflow_runs.workflow_name` enum to remove `nightly_pulse` (or keep as a legacy value with no active code path — document the choice in the migration comment).
- The Correlation Agent (Step 3.2) and `correlation_snapshots` table remain — they feed the Nudge Category Generator (Phase 7). Only the nightly auto-nudge path (Nudge Composer triggered on a schedule) is removed.
- Update `docs/architecture.md` "What each role can see" table — remove rollup rows from Leadership and Admin; update the workflow list to remove `nightly_pulse`.

*Frontend:*
- Delete `frontend/src/components/RollupView/` and any routes pointing to it.
- Remove the "Rollups" / "Team rollups" nav link from Leadership sessions.
- If any Leadership landing page defaulted to the rollup view, redirect Leadership users to the Nudges sent-history panel (`/nudges`) instead.

**Scenario tests:**
- *A `GET /rollups/` request returns 404 after removal.*
- *Calling the `nightly_pulse` workflow (if an endpoint existed) returns a clear error, not a silent 200.*
- *The admin-initiated nudge campaign workflow still completes correctly end-to-end — Correlation Agent and nudge campaign path are unaffected.*

**Definition of done:** all three pass; `rollups` table is absent from the schema; rollup-related frontend components are deleted; `docs/architecture.md` reflects the new role table.

---

### Step 9.2 — Admin/Leadership practitioner view — Skill Radar only (read-only)

**Goal:** when an Admin user selects a practitioner to view, they see exactly one tab — the Skill Radar — and all interactive controls are absent. The profile details are surfaced as a compact read-only panel alongside the radar.

**Preconditions:** 9.1.
**Context to load:** `docs/architecture.md` (Auth — What each role can see).

**Build:**

*Frontend — Admin practitioner view (`/admin/practitioners/:id`):*
- Renders only the Skill Radar component from Step 6.7, scoped to the selected practitioner.
- **Tab strip**: a single tab "Skill Radar". Quiz, Adoption Trends, Nudge Inbox, Certifications tabs are not rendered for this view. There is no tab switcher — just the radar.
- **Interactive controls hidden**: "Regenerate path" button is not shown (admins cannot trigger profiler runs on behalf of another practitioner). "Edit profile →" link is absent. There is no self-assessment toggle.
- **Read-only profile panel** (sidebar or header strip, not a tab): shows practitioner name, active profile name, chosen certification (code + full name), and the date the profile was last saved — all plain text, no action buttons.
- Admin navigation: `GET /admin/practitioners` list page already exists; each row/card links to this dedicated view (`/admin/practitioners/:id`).
- Leadership sessions follow the same view — they can navigate to the same practitioner radar view.

*Backend:*
- Existing routes (`GET /practitioners/{id}/skill-profile`, `GET /practitioners/{id}/profiles`) already require `require_admin` or `require_admin_or_leadership`. No new routes needed.
- Verify that `GET /practitioners/{id}/profiles/{profile_id}` returns the `is_locked` field so the frontend can confirm it (already true after Step 9.3, but include the field now for consistency).

**Scenario tests (Playwright):**
- *An admin who navigates to `/admin/practitioners/:id` sees exactly one tab labelled "Skill Radar" and no other tabs.*
- *The Skill Radar tab for an admin-viewed practitioner has no "Regenerate path" button and no "Edit profile" link.*
- *The read-only profile panel shows the practitioner's certification code and profile name as plain text.*

**Definition of done:** all three pass.

---

### Step 9.3 — Profile lockdown after first full submission

**Goal:** once a practitioner completes the full profile wizard (questionnaire → certification → skill ratings → save), the profile is permanently locked. They can view it, activate/deactivate it, or delete it — but they cannot edit the questionnaire answers, change the certification, or re-rate the skills on that profile. To change direction, they create a new profile.

**Preconditions:** 9.2.
**Context to load:** `docs/data-model.md` (practitioner_profiles table), Step 6.5 for the save endpoint.

**Build:**

*Backend:*
- New migration: add `is_locked` (boolean, default `false`, non-nullable) to `practitioner_profiles`.
- In `POST /practitioners/{id}/profiles/{profile_id}/skill-assessments` (the final wizard step): after successfully writing all skill rows, immediately set `is_locked = true` on the profile within the same transaction. This is the lock trigger — saving skill ratings is the definitional "done" moment for a profile.
- `PATCH /practitioners/{id}/profiles/{profile_id}`: if `is_locked = true`, return `HTTP 403` with body `{"detail": "Profile is locked and cannot be edited. Create a new profile to make changes."}`.
- `POST /practitioners/{id}/profiles/{profile_id}/skill-assessments`: if `is_locked = true`, return `HTTP 403` with the same message. (Prevents a second save attempt after locking.)
- `GET /practitioners/{id}/profiles` and `GET /practitioners/{id}/profiles/{profile_id}`: expose `is_locked` in the response body.
- `PATCH /practitioners/{id}/profiles/{profile_id}/activate` and `DELETE /practitioners/{id}/profiles/{profile_id}`: unaffected by `is_locked` — practitioners can still activate or delete locked profiles.
- The `PATCH /auth/me` active-profile response (added in Step 6.6): include `is_locked` so the frontend can gate controls without an extra round-trip.

*Frontend:*
- `BuildProfilePage`: for profiles where `is_locked = true`, replace the "Edit" card action with a "View" button that opens a non-editable summary modal or navigates to a read-only profile detail page.
- `ProfileWizard` (Step 6.4): on entry via a wizard URL that carries a `profile_id`, check `is_locked`; if true, redirect immediately to `BuildProfilePage` with a toast: `"This profile is locked. Create a new profile to make changes."`
- `ProfileSkillAssessmentPage` (Step 6.5): if `is_locked = true`, render all skill sliders/pickers as `disabled` and show a banner at the top: `"This profile is saved and locked. Your skill ratings cannot be changed."`
- "Delete" action: remains available regardless of lock state. (Practitioners can delete a locked profile; they just cannot edit it.)
- "New profile" CTA on `BuildProfilePage` and the banner message in the locked state both link clearly to starting the wizard fresh.

**Scenario tests:**
- *Completing the full wizard (questionnaire + certification + skills) locks the profile — a subsequent `PATCH /practitioners/{id}/profiles/{profile_id}` request returns 403.*
- *A locked profile card on `BuildProfilePage` shows "View" in place of "Edit".*
- *Navigating to the wizard URL for a locked profile redirects to `BuildProfilePage` with a "locked" toast rather than showing the editable wizard step.*

**Definition of done:** all three pass; migration runs cleanly; no existing scenario tests (for unlocked flows) are broken.

---

### Step 9.4 — Quiz-only mastery engine

**Goal:** `skill_profile_snapshots` are computed exclusively from quiz-attempt signals. Self-assessment ratings stored in `profile_skill_assessments`, certification completion signals, and project-history events no longer contribute to the radar. The initial profile self-assessment is preserved in the DB as part of the locked profile record, but is not passed to the Skill Profiler.

**Preconditions:** 9.3.
**Context to load:** `docs/architecture.md` (Skill Profiler agent entry), `docs/data-model.md` (skill_profile_events, profile_skill_assessments).

**Design note — starting state:**
- A new practitioner who has just locked their first profile will have all Skill Radar mastery scores at 0% until they answer quiz questions. This is intentional — the radar is earned, not estimated.
- The **domain gap chart** (added in Phase 10) is different: it starts with an LLM-derived estimate from the self-assessment ratings (Domain Scorer Agent, Step 10.2), so the gap chart is not empty on day one. This estimate is flagged as tentative and is replaced domain-by-domain as cert-evaluated quiz answers come in.
- The Skill Radar empty state (Step 6.7) should be updated to say: *"Your radar starts at zero and grows as you answer quiz questions. Click "Regenerate path" after each quiz session to update it."*
- "Regenerate path" remains the manual trigger — there is no background re-profiling.

**Build:**

*Backend:*
- In `backend/app/workflows/generate_learning_path.py` (the workflow that calls the Skill Profiler): change the query that assembles profiler input to filter `skill_profile_events` to `source = 'quiz_attempt'` only. Remove the code that fetches `profile_skill_assessments` rows and merges them in.
- In `backend/app/agents/skill_profiler.py`: remove the `self_assessment_ratings` input field from `SkillProfilerInput` (or mark it as deprecated/unused); the profiler now receives only quiz-attempt events.
- Update `prompts/skill_profiler.md`: remove all references to self-assessment or certification signals. The prompt now reads only quiz attempts (score, skill, item difficulty) and computes mastery from those alone.
- The MCP `mcp-learning-portal` integration (certification completions from external portal) is also removed from the profiler's input construction — it was already degraded for NVIDIA in Phase 8; now it is removed for all providers, keeping the profiler's input contract clean.
- `skill_profile_events` rows with `source IN ('self_assessment', 'certification', 'project_history')` remain in the database — they are not deleted — but they are simply not queried by the profiler workflow.

*Frontend:*
- `SkillRadar` (Step 6.7): update the empty-state copy: *"Your radar starts at zero. Answer quiz questions and click 'Regenerate path' to see your mastery levels fill in."*
- Remove any remaining copy or tooltip that implies self-rating affects the radar scores.

**Scenario tests:**
- *A practitioner with a locked profile whose `profile_skill_assessments` show `signal_strength = 0.9` on skill X — and zero quiz attempts — has a mastery score of 0.0 on skill X after running the Skill Profiler.*
- *After a practitioner submits a correct quiz answer for skill Y and clicks "Regenerate path", skill Y's mastery score increases above 0.*
- *`skill_profile_events` rows with `source = 'self_assessment'` are present in the DB but do not change the snapshot when the profiler runs.*

**Definition of done:** all three pass; `prompts/skill_profiler.md` contains no self-assessment or certification signal language.

---

### Steps 9.5 / 9.6 / 9.7 — merged into Phase 10

> These steps have been absorbed into Phase 10 in dependency order. Full specs live there:
> - **9.5** (progressive scoring) → **Step 10.7**
> - **9.6** (auto-refresh) → **Step 10.8**
> - **9.7** (trend indicators) → **Step 10.11**
>
> The domain foundation (10.1–10.6) must be in place before any of the above: the round-ceiling model applies to both skill and domain scores, auto-refresh items must be domain-tagged from generation one, and the trend chips decorate the domain gap chart (10.9) not the old skill-snapshot bars.

---

# Phase 10 — Certification-Domain Alignment & Mastery Refinements

This phase does three things in dependency order:

**Part A — Domain Model & Live Refresh (Steps 10.1–10.4):** model every certification's official exam domains, make that data live-refreshable rather than hardcoded forever, and give admins a one-click refresh flow. AI certifications change fast — CCAR-P didn't exist a few months ago; AWS retired ML Specialty and split it into MLA-C01 and a GenAI track in the same window; Google Cloud releases new credentials quarterly. A hardcoded seed file becomes stale within 6 months and requires a code change to update. Steps 10.2–10.4 replace the static seed with a versioned, admin-refreshable system driven by the Cert Domain Discovery Agent.

**Domain versioning principle:** exam domain data is frozen per profile at lock time. When an admin refreshes domains (creating a new version), existing practitioners' domain scores are unaffected — their profiles reference the version that was current when they locked. New profiles automatically inherit the latest version. This guarantees a practitioner who started studying for AIF-C01 in Q1 is not silently re-evaluated against a Q3 exam revision they haven't seen.

**Part B — Domain Scoring & Item Tagging (Steps 10.5–10.6):** once versioned domain infrastructure is in place, the Domain Scorer Agent maps self-assessments to initial domain readiness scores at profile-lock time, and the Item-Writer is extended to tag every generated item with its cert domain and whether it is directly exam-evaluated.

**Part C — Mastery Refinements (Steps 10.7–10.11):** add the progressive-scoring model, auto-refresh, domain gap chart scoring, quiz color-coding, and visual trend indicators — all of which were originally Phase 9.5–9.7 but have been moved here because they depend on the Part A domain model being in place:
- The round-ceiling model (10.7) must apply to both skill radar AND domain scores — so domain tables (10.1) come first.
- Auto-refresh (10.8) generates new items that are domain-tagged from day one — so domain-aware item writer (10.6) comes first.
- The domain gap chart (10.9) is what the trend indicators (10.11) decorate — so 10.9 before 10.11.

**Preconditions:** 9.4 (quiz-only mastery engine; the two-tier scoring model built here depends on the quiz-first principle already being in place).

---

### Step 10.1 — Certification exam domains data model & seed data 👤

**Goal:** model every active certification's official exam domains (the real sections the exam grades you on) and make those domains the organizing principle for items, gap scores, and readiness reporting. Make certification mandatory on profiles.

**Preconditions:** 9.4.
**Context to load:** `docs/data-model.md` (certification_domains, certification_domain_scores), `docs/human-in-the-loop.md` (Step 10.1 entry).

**Build:**

*Schema (new migration):*
- `certification_domains` table — see `docs/data-model.md` for column list and seeded domain content.
- Add `certification_domain_id` (nullable FK → `certification_domains`) and `is_cert_evaluated` (boolean, default `false`) to `items`. Existing items get `NULL / false` — these are legacy; new items generated after this step must always have both fields set.
- Make `practitioner_profiles.certification_id` NOT NULL. Migration: if any existing profiles have `certification_id = NULL`, require a default cert to be set before the migration runs (or block on this interactively).
- `certification_domain_scores` table — see `docs/data-model.md` for column list and source enum.

*Seed data (`backend/seed/certification_domains.py`):*
- Populate `certification_domains` for every `is_active = true` cert in the catalog, using the domain list in `docs/data-model.md` as the starting point.
- Verify each entry against the official exam guide PDF before committing the seed — do not rely solely on the table in `docs/data-model.md` if the cert has been updated since it was written. `last_verified_at` on the parent `certifications` row is your staleness indicator.

**Scenario tests:**
- *Every active certification has at least 3 domain rows* — no cert is left with an empty domain list.
- *Domain weights sum to 100 per certification* — `SUM(weight_pct) = 100` (allow ±1 for rounding) for every `certification_id` group in `certification_domains`.
- *`practitioner_profiles.certification_id` accepts NULL in the schema — this is rejected at the API layer (422 validation), not the DB layer* — or, if the column is made truly NOT NULL at the DB level, a migration guard must handle existing null rows before applying the constraint.

**Definition of done:** all three pass; every active cert has seeded domain rows; `certification_domain_id` and `is_cert_evaluated` columns exist in `items`; `certification_domain_scores` table exists; migration runs clean.

> 👤 **Human-in-the-loop:** validate the seeded domain data against each cert's official exam guide before implementing the steps that depend on it. This bootstrap data is version 1 — from Step 10.3 onward it is superseded by the Cert Domain Discovery Agent whenever an exam is revised or a new cert is added. See `docs/human-in-the-loop.md`.

---

### Step 10.2 — Domain versioning data model — live-refreshable domain versions

**Goal:** make certification domain data version-aware so that (a) a practitioner's domain scores always reference the exact domain definitions that were current when their profile was locked — no retroactive resets when an admin refreshes domain data; (b) an admin refresh creates a new version without breaking existing profiles or their domain scores; (c) new profiles automatically inherit the latest approved version; (d) the bootstrap seed from Step 10.1 becomes version 1, not a forever-immutable truth.

**Preconditions:** 10.1.
**Context to load:** `docs/data-model.md` (certification_domain_versions, certification_domain_proposals tables), `backend/alembic/versions/012_certification_domains.py`.

**Build:**

*New migration (013):*
- New table `certification_domain_versions`:
  - `id` (UUID PK), `certification_id` (FK → certifications), `version_label` (text — e.g. "bootstrap-step-10.1" or "2025-Q1-refresh"), `is_current` (boolean — partial unique index on `(certification_id) WHERE is_current = true` enforces exactly one current version per cert), `source_notes` (text — where the data came from), `agent_run_id` (nullable FK → agent_runs — null for bootstrap; set for agent-driven refreshes), `created_by_admin_id` (nullable FK → admin_users — null for bootstrap), `created_at`
- Add `domain_version_id` (FK → certification_domain_versions, nullable) to `certification_domains`. All existing rows are backfilled: the migration creates one bootstrap `certification_domain_versions` row per cert (is_current = true, version_label = "bootstrap-step-10.1") and sets `domain_version_id` on each existing domain row accordingly.
- Add `domain_version_id` (FK → certification_domain_versions, nullable) to `practitioner_profiles`. Null for profiles locked before this step; set at profile lock time from Step 10.5 onward.
- New table `certification_domain_proposals`:
  - `id` (UUID PK), `certification_id` (nullable FK → certifications — null when proposing a brand-new cert), `cert_code` (text), `cert_name` (text), `proposed_domains` (JSONB — list of {sequence_order, domain_name, domain_description, weight_pct}), `source_notes` (text), `agent_run_id` (FK → agent_runs), `status` (`pending_review` | `approved` | `rejected`), `reviewed_by_admin_id` (nullable FK → admin_users), `reviewed_at` (nullable timestamp), `rejection_notes` (nullable text), `created_at`

*Update seed (`backend/seed/certification_domains.py`):*
- After inserting domain rows, create one `certification_domain_versions` row per cert (is_current = true, version_label = "bootstrap-step-10.1") and set `domain_version_id` on each domain row. Idempotent: if a bootstrap version already exists for a cert, reuse it.

*New ORM models:* `CertificationDomainVersion`, `CertificationDomainProposal`. Add `domain_version_id` FK to `CertificationDomain` and `PractitionerProfile` ORM models.

*New API endpoints (admin-only, `require_admin`):*
- `GET /admin/cert-domain-versions` — list all versions per cert, ordered newest-first per cert.
- `GET /admin/cert-domain-proposals` — list proposals by status (default: `pending_review`).

**Scenario tests:**
- *The migration creates exactly one `certification_domain_versions` row per active cert, each with `is_current = true`.*
- *Every existing `certification_domains` row has a non-null `domain_version_id` after migration — no orphaned domain rows.*
- *Inserting a second `is_current = true` row for the same cert is rejected — the partial unique index fires.*

**Definition of done:** all three pass; migration runs clean; `GET /admin/cert-domain-versions` returns versioned data; Step 10.1 scenario tests are still green.

---

### Step 10.3 — Cert Domain Discovery Agent — LLM-driven exam domain research & refresh 👤

**Goal:** an LLM agent that researches the current official exam domains and weights for any certification and returns structured proposals for admin review. This removes the need to edit seed files when an exam is revised or a new certification enters the catalog. When the admin approves a proposal, a new version is published — existing profiles are unaffected, new profiles use the updated domains.

**Preconditions:** 10.2.
**Context to load:** `docs/architecture.md` (agent #11 — Cert Domain Discovery), `docs/human-in-the-loop.md` (Step 10.3 entry), `backend/app/agents/base.py`.

**Build:**

*New agent — `backend/app/agents/cert_domain_discovery.py` + `agents/prompts/cert_domain_discovery.md` 👤:*
- `CertDomainDiscoveryInput`:
  - `cert_code: str`, `cert_name: str`, `provider_name: str`
  - `known_source_url: str | None` — official exam guide URL if already known; agent should prioritize this
  - `current_domains: list[{domain_name, weight_pct}] | None` — existing data for comparison; agent notes any changes
  - `refresh_reason: str | None` — context for the agent (e.g. "cert revised 2025-Q1", "initial discovery")
- `CertDomainDiscoveryOutput`:
  - `cert_code: str`
  - `proposed_domains: list[{sequence_order, domain_name, domain_description, weight_pct}]`
  - `source_notes: str` — where the agent found the data, with explicit acknowledgment of uncertainty
  - `changes_from_current: list[str] | None` — bullet diff vs. current_domains; null if no previous
  - `confidence: Literal["high", "medium", "low"]` — high = verified from official guide in training data; medium = inferred from curriculum; low = uncertain or no reliable source found
  - `suggested_source_url: str | None` — URL the admin should verify before approving
- Persist output to `certification_domain_proposals` (status = `pending_review`), linked to the `agent_runs` row.

*New API endpoints (admin-only, `require_admin`):*
- `POST /admin/cert-domains/discover` — body: `{cert_code, cert_name, provider_name, known_source_url?, refresh_reason?}` — triggers agent for one cert; returns the created proposal.
- `POST /admin/cert-domains/discover-all` — triggers discovery for all active certs via `asyncio.gather`; returns list of proposals.
- `POST /admin/cert-domain-proposals/{id}/approve` — creates new `certification_domain_versions` row (is_current = true) + new `certification_domains` rows; flips old version is_current = false; sets proposal status = `approved`. If `certification_id` is null (new cert), creates a `certifications` row with `is_active = false` for separate admin activation.
- `POST /admin/cert-domain-proposals/{id}/reject` — body: `{rejection_notes: str}` — sets status = `rejected`; no domain rows are touched.

**Scenario tests:**
- *Given a stub agent response with 5 valid domain rows summing to 100%, the discover endpoint persists a `certification_domain_proposals` row with status `pending_review` linked to an `agent_runs` row.*
- *Approving a proposal creates a new `certification_domain_versions` row with `is_current = true` and flips the previous version to `is_current = false` — exactly one current version per cert.*
- *Approving a proposal for a cert_code not in `certifications` creates a new cert row with `is_active = false`.*
- *Rejecting a proposal sets `status = 'rejected'` and persists rejection notes without touching any `certification_domains` rows.*

**Definition of done:** all four pass against the stub Claude client; `cert_domain_discovery.py` and `prompts/cert_domain_discovery.md` exist; all four endpoints are guarded by `require_admin`.

> 👤 **Human-in-the-loop:** write `agents/prompts/cert_domain_discovery.md` yourself before implementing. This agent's output (when approved) replaces the exam domain data all practitioners are tested against. A prompt that confidently fabricates plausible-sounding but incorrect domain names is more dangerous than one that says "I cannot find a reliable source" — at least a refusal is visible. Own the confidence-level vocabulary, the uncertainty language, and the rule that the agent must flag low-confidence outputs rather than filling in gaps from imagination. See `docs/human-in-the-loop.md`.

---

### Step 10.4 — Admin "Refresh Certification Domains" UI

**Goal:** admins can trigger domain discovery for any certification, review proposed updates side-by-side with the current version, and publish or reject changes — all from a self-service UI page, with no code changes or redeployments required.

**Preconditions:** 10.3.
**Context to load:** `docs/architecture.md` (Auth §What each role can see).

**Build:**

*New page `frontend/src/pages/CertDomainManagementPage.tsx`*, routed at `/admin/cert-domains`. Route guard: Admin-only for refresh/approve/reject controls; Leadership sessions see read-only mode.

- **Current Versions panel**: one card per active cert showing version label, published date, source notes, and confidence badge. Cards are collapsible to show the full domain list (sequence_order, domain_name, weight_pct).
- **Refresh controls (admin only):** a primary **"Refresh all certs"** button calls `POST /admin/cert-domains/discover-all` with a spinner. Individual cert cards also have a **"Refresh this cert"** button. Both append results to the Proposals panel below.
- **Proposals panel**: each pending proposal shows:
  - Cert code + name + confidence badge (green = High, amber = Medium, red = Low).
  - Side-by-side diff: current domains vs. proposed domains. New-cert proposals show only the proposed column.
  - `source_notes` and a clickable **"Verify source ↗"** link (`suggested_source_url`) — admin should verify before approving.
  - `changes_from_current` rendered as a bulleted diff (shown only if non-empty).
  - **Approve** button with confirmation: *"Approving will create a new domain version for [cert code]. Practitioners with locked profiles won't be affected — their scores reference the version in place at lock time."*
  - **Reject** button: requires a short rejection-notes field.
- **Version history panel**: collapsible "Version history" per cert — version_label, created_at, created_by, agent run link.
- **New cert proposals section**: discovery results for cert_codes not yet in the catalog. Approving creates the cert row (is_active = false); a separate "Activate cert" toggle calls the existing certs API once the admin is satisfied.

*Admin nav:* add "Cert Domains" link under admin navigation, hidden from practitioner sessions.

**Scenario tests (Playwright):**
- *Admin clicks "Refresh all certs" and sees at least one proposal card appear with Approve and Reject controls.*
- *Approving a proposal updates the Current Versions panel to show the new version label and date.*
- *Rejecting a proposal with notes removes it from the pending list without changing the current version.*
- *A Leadership user sees the Current Versions panel but Refresh/Approve/Reject controls are disabled.*

**Definition of done:** all four pass; admin can complete the full refresh → review → approve flow against a live backend without touching any files.

---

### Step 10.5 — Domain Scorer Agent — self-assessment → initial domain scores

**Goal:** when a practitioner locks their profile (after saving skill ratings in Step 6.5), use the self-assessment proficiency ratings to compute an initial estimate for each certification domain score. This gives the gap chart a non-zero, LLM-reasoned starting point before any quizzes are taken — so practitioners can immediately see where the model thinks they are relative to each exam domain, and which domains are the biggest gaps to close.

**Preconditions:** 10.2.
**Context to load:** `docs/architecture.md` (Domain Scorer Agent entry), `docs/data-model.md` (certification_domain_scores, certification_domain_versions), `backend/app/agents/base.py`.

**Build:**

*New agent — `backend/app/agents/domain_scorer.py` + `prompts/domain_scorer.md`:*
- `DomainScorerInput`:
  - `certification_id: str`
  - `certification_domains: list[{id, name, description, weight_pct}]` — passed in from the workflow, not fetched inside the agent.
  - `skill_assessments: list[{skill_name, signal_strength}]` — the practitioner's self-ratings from `profile_skill_assessments`.
- `DomainScorerOutput`:
  - `domain_scores: list[{certification_domain_id, initial_score: float, confidence: float, rationale: str}]`
  - Confidence is capped at 0.5 — these are estimates, not measured performance.
- The agent reasons over the mapping: given the domain description (e.g., "Fundamentals of Generative AI — covers tokenization, fine-tuning, RAG, and prompt engineering concepts") and the skill ratings, what initial readiness score is plausible for this domain?
- Persist output to `certification_domain_scores` with `source = 'self_assessment_estimate'`. **Never overwrite a row that already has `source = 'quiz_derived'`** — the self-assessment estimate is only the fallback / initial state; quiz performance takes permanent precedence.

*Integration:*
- In `POST /practitioners/{id}/profiles/{profile_id}/skill-assessments` (the profile-locking endpoint), after writing `profile_skill_assessments` rows and setting `is_locked = true`: (a) look up the cert's current `certification_domain_versions` row and set `practitioner_profiles.domain_version_id` to its `id` — this freezes the domain version for this profile so a future admin refresh never retroactively shifts this practitioner's baseline; (b) call the Domain Scorer Agent using the `certification_domains` rows for that pinned version and persist its output to `certification_domain_scores`. This is the only time self-assessment ratings influence scores — at lock time, one shot.
- `DomainScorerAgent` is not called by the `generate_learning_path` workflow — it runs only at lock time. The workflow uses the already-computed `certification_domain_scores` directly.

**Scenario tests:**
- *A practitioner who rates themselves Advanced (signal_strength ≥ 0.8) in skills that map to Domain 1 gets an initial domain score above 0.3 for Domain 1 after profile lock.*
- *A practitioner who rates themselves None (signal_strength = 0.0) on all skills gets initial domain scores ≤ 0.1 on all domains.*
- *Running the Domain Scorer again after the practitioner has taken cert-evaluated quizzes does not overwrite any `quiz_derived` domain score row.*

**Definition of done:** all three pass; `domain_scorer.py`, `prompts/domain_scorer.md`, and the profile-locking integration exist; the stub Claude client fixture covers `DomainScorerAgent`.

---

### Step 10.6 — Domain-aware item writer & tagging

**Goal:** every item generated from this step forward carries its certification domain and whether it is directly evaluated in the exam. Items cover all of the practitioner's cert domains proportionally to their exam weight. Practitioners and the scoring system can distinguish "this question counts toward my exam readiness" from "this is useful context."

**Preconditions:** 10.5.
**Context to load:** `docs/architecture.md` (Item-Writer agent, Certification-Domain Alignment section), `backend/app/agents/item_writer.py`, `backend/app/agents/prompts/item_writer.md`, `docs/human-in-the-loop.md` (Step 10.6 entry).

**Build:**

*Backend:*
- Extend `ItemWriterInput` with:
  - `certification_id: str | None`
  - `certification_domains: list[{id, name, description, weight_pct}] | None` — the cert's domains; `None` for non-cert-aware generation (legacy path, fallback only).
- Extend `ItemWriterOutput` per-item with:
  - `certification_domain_id: str | None`
  - `is_cert_evaluated: bool`
- After the Item-Writer Agent returns its output, persist `certification_domain_id` and `is_cert_evaluated` to the `items` table rows.
- Domain coverage policy (encoded in `prompts/item_writer.md`):
  - Generate at least one item per domain, proportionally distributed by `weight_pct` (a domain worth 28% gets roughly 1.4× as many items as a domain worth 20%).
  - Supplementary items (`is_cert_evaluated = false`) may be generated for context — e.g., conceptual background that helps understanding but isn't in the exam blueprint. These still get `certification_domain_id` (they're related to a domain, just not directly tested).
- In `generate_learning_path` workflow: when the practitioner has an active cert, pass that cert's `certification_domains` to `ItemWriterInput`.

*Prompt update (`prompts/item_writer.md`):*
- Add domain-tagging instructions: the agent must label each item with the domain it tests and set `is_cert_evaluated = true` if the topic appears in the official exam blueprint, `false` if it supports understanding but isn't directly assessed.
- 👤 This is the critical judgment call: the prompt must teach the agent to distinguish "in the blueprint" from "related but not evaluated" correctly. Review the prompt against the official exam guide for your primary cert before accepting it at scale.

**Scenario tests:**
- *Given a cert with 5 domains and a request for 10 items, at least 5 distinct `certification_domain_id` values appear in the output — no single domain monopolizes all items.*
- *Every item in the output has `is_cert_evaluated` set (not null or missing).*
- *An item whose `is_cert_evaluated = false` still has a `certification_domain_id` — it is domain-aware even though it's supplementary.*

**Definition of done:** all three pass; `certification_domain_id` and `is_cert_evaluated` are populated on all items generated after this step; legacy items remain `NULL / false` and are handled gracefully by scoring logic.

---

### Step 10.7 — Progressive quiz-round scoring model (scores can rise AND fall)

**Goal:** a practitioner cannot achieve 100% mastery on a skill from a single set of quiz questions. Mastery rises progressively across multiple completed rounds, following a ceiling formula that guarantees meaningful effort is required to approach full mastery. The same ceiling logic applies to both the broad Skill Radar (skill-level scores) and the domain gap chart (domain-level scores).

**Preconditions:** 10.6 (domain-aware items exist; `generation` column from this migration is also needed by the auto-refresh step that follows).
**Context to load:** `docs/data-model.md` (items, attempts tables), `backend/app/agents/skill_profiler.py`.

**Design — round-based ceiling model:**

A **round** is defined as: the practitioner has attempted every available item in the current generation for a skill at least once (see Step 10.8 for the generation concept). The mastery ceiling after N completed rounds follows:

```
ceiling(N) = 1 − (0.5)^N
```

| Rounds completed | Max mastery |
|---|---|
| 0 | 0% |
| 1 | 50% |
| 2 | 75% |
| 3 | 87.5% |
| 4 | 93.75% |
| 5 | 96.875% |

**Scoring model — ceiling × recency-weighted accuracy:**

The actual mastery score = `ceiling(rounds_completed) × weighted_accuracy`, where `weighted_accuracy` weights recent rounds more heavily than earlier ones. This means **wrong answers in a later round lower the mastery score**, even when earlier rounds went well — a practitioner who cruised through round 1 then struggles in round 3 will see their radar drop.

Weighting formula (recency-weighted average across all completed rounds):

```
weighted_accuracy = Σ (accuracy[i] × weight[i]) / Σ weight[i]
weight[i] = 2^(i−1)          # round 1 has weight 1, round 2 has weight 2, round 3 has weight 4, …
```

Example: rounds 1–3 accuracy = [1.0, 0.9, 0.4] → weights = [1, 2, 4] → weighted accuracy ≈ 0.61 → ceiling(3) × 0.61 = 0.875 × 0.61 ≈ 53%. The bad round-3 performance tanks a score that was on track for 87%. That is intentional — it reflects actual current knowledge, not a historical peak.

**There is no ratchet.** Mastery scores can and should go down when a practitioner performs poorly in a later round. A practitioner who was overconfident and fails round 3 deserves to see their radar decline. The ceiling itself never decreases (completing a round is permanent), but the actual score within that ceiling is always recomputed from the full weighted accuracy.

**Build:**

*Backend:*
- New migration: add `generation` (integer, default 1, non-nullable) column to `items`. All existing items get `generation = 1`. When new items are generated for a skill (Step 10.5), they receive `generation = max(existing for that skill) + 1`.
- New utility function `backend/app/agents/round_metrics.py` — `compute_round_metrics(practitioner_id: UUID, skill_id: UUID, db: AsyncSession) -> RoundMetrics`:
  - Queries `attempts` joined to `items` for this practitioner and skill.
  - Groups by `items.generation` to determine which rounds are fully completed (all items in that generation have at least one attempt).
  - Computes `per_round_accuracy: list[float]` in generation order, then applies the recency-weighted formula.
  - Returns: `rounds_completed: int`, `per_round_accuracy: list[float]`, `mastery_ceiling: float`, `weighted_accuracy: float`, `current_mastery_score: float`.
- Update `generate_learning_path` workflow: after querying quiz-attempt events (Step 9.4), also call `compute_round_metrics` for each skill and pass the results to `SkillProfilerInput` as `quiz_round_metrics: list[RoundMetricsPerSkill]`.
- Update `SkillProfilerInput` to include `quiz_round_metrics` alongside raw attempt events.
- Update `prompts/skill_profiler.md` to instruct the agent to use `mastery_ceiling` and `current_mastery_score` from `quiz_round_metrics` as the primary mastery signal and to note that scores can decrease when recent round accuracy is poor.
- Also return `previous_mastery_score` in `RoundMetrics` (the value from the previous `skill_profile_snapshots` row before this profiler run) so the API can expose the delta to the frontend for visual indicators (Step 10.11).

**Scenario tests:**
- *A practitioner who answers all generation-1 items for skill X with 100% accuracy achieves `current_mastery_score ≤ 0.50` — the round-1 ceiling is enforced.*
- *A practitioner who completes rounds 1 and 2 with 100% accuracy achieves `current_mastery_score > 0.50` and `≤ 0.75`.*
- *A practitioner whose round-3 accuracy is 40% (well below their round-1 and round-2 performance) achieves a `current_mastery_score` lower than their score after round 2 — incorrect answers in a recent round pull the score down.*

**Definition of done:** all three pass; `generation` column exists in `items`; `compute_round_metrics` has its own unit test file; the third scenario explicitly confirms score reduction on a bad round.

---

### Step 10.8 — Auto-refresh quiz questions after round exhaustion

**Goal:** when a practitioner has answered all available items for a skill, the system automatically generates a new set of questions (next generation) so the practitioner can continue progressing. New items are domain-tagged from day one (using the domain-aware Item-Writer from Step 10.6) so the domain gap chart stays accurate across all rounds. The Quiz Runner surfaces a brief "round complete" moment before presenting the new items.

**Preconditions:** 10.7.
**Context to load:** `docs/architecture.md` (Item-Writer agent, Certification-Domain Alignment section), `backend/app/agents/item_writer.py`.

**Build:**

*Backend:*
- New helper `get_unanswered_items(practitioner_id: UUID, skill_id: UUID, db: AsyncSession) -> list[Item]`: returns items in the current (highest) generation for a skill that have zero attempts by this practitioner.
- Update the quiz item endpoint (`GET /practitioners/{id}/quiz-items` or the existing skill-items route):
  1. Call `get_unanswered_items(practitioner_id, skill_id)`.
  2. If the result is non-empty: return those items normally with `generation_refreshed: false`.
  3. If the result is empty (all current-generation items answered): trigger `ItemWriterAgent` synchronously to generate a new set for this skill with `generation = max_existing + 1`. Cap generation size via env var `QUIZ_ITEMS_PER_GENERATION` (default: 5). Return the new items with `generation_refreshed: true` and `new_generation: int`.
- The Item-Writer prompt for refresh rounds should receive context that these are follow-up items (harder, or approaching the topic from a different angle). Pass `is_refresh_round: true`, `prior_generation_count: int`, and the cert's `certification_domains` so refreshed items are also domain-tagged and `is_cert_evaluated` is set correctly.
- New `agent_runs` row is written for each Item-Writer call (existing behavior — no change needed).
- Env var `QUIZ_ITEMS_PER_GENERATION` defaults to 5; document in `.env.example`.

*Frontend:*
- `QuizRunner` (Step 6.8): detect `generation_refreshed: true` in the endpoint response. When true, display a brief interstitial panel (1–2 seconds, or dismiss-on-click):
  - Heading: **"Round complete! 🎯"**
  - Sub-text: **"You've answered all available questions for this skill. New challenges are loading…"**
  - After the interstitial, render the new items normally — the "Next" button logic continues as before.
- Quiz tab skill selector: add a small indicator next to each skill showing the current round number: `"Round N"` (read from `new_generation` or derive from attempt counts). This gives practitioners a sense of progress without surfacing the ceiling formula itself.
- Empty-state handling: if the Item-Writer call fails during auto-refresh, show a friendly error instead of crashing: *"Couldn't load new questions right now. Try clicking Regenerate path or refreshing the page."*

**Scenario tests:**
- *When a practitioner has answered all generation-1 items for skill X, the quiz endpoint returns generation-2 items with `generation_refreshed: true` — no error, no empty response.*
- *The generation-2 items have different `id` values from the generation-1 items — they are new questions, not duplicates.*
- *Generation-2 items have `certification_domain_id` set (not NULL) — domain tagging carries over to refreshed rounds.*
- *The `QuizRunner` displays the "Round complete" interstitial when `generation_refreshed = true` and then shows the new questions.*

**Definition of done:** all four pass; `QUIZ_ITEMS_PER_GENERATION` is documented in `.env.example`; a failed Item-Writer call surfaces a user-facing error message rather than a crash; refreshed items always carry domain tags.

---

### Step 10.9 — Certification domain gap scoring workflow & UI

**Goal:** compute per-domain readiness scores from cert-evaluated quiz answers and replace the current "Top skill gaps" bar chart with a domain gap chart that shows the practitioner exactly how ready they are for each section of their certification exam. Domain scores respect the same round-ceiling model established in Step 10.7.

**Preconditions:** 10.8.
**Context to load:** `docs/data-model.md` (certification_domain_scores, two-tier scoring table), `backend/app/workflows/generate_learning_path.py`, Step 10.7 (round-based ceiling model that domain scoring also respects).

**Build:**

*Backend:*
- New utility function `compute_domain_scores(practitioner_id, certification_id, db) → list[DomainScore]`:
  - Queries `attempts` joined to `items` where `is_cert_evaluated = true` and `items.certification_domain_id` belongs to the given cert.
  - Groups by `certification_domain_id`.
  - Applies the recency-weighted accuracy formula from Step 10.7 (and the round ceiling if round metrics are available — domain scores respect the same ceiling model as broad skill scores).
  - Upserts `certification_domain_scores` with `source = 'quiz_derived'`. **Never overwrites** an existing `quiz_derived` row with a `self_assessment_estimate`.
- Call `compute_domain_scores` in the `generate_learning_path` workflow after the Skill Profiler step.
- New API endpoint: `GET /practitioners/{id}/certification-domain-scores?certification_id={id}` — returns `[{domain_name, weight_pct, sequence_order, mastery_score, gap_score, source}]` ordered by `sequence_order`. Used by the gap chart.
- The existing `GET /practitioners/{id}/skill-profile` endpoint remains unchanged — it continues to drive the Skill Radar.

*Frontend:*
- New component `CertDomainGapChart` — replaces the current "Top skill gaps" progress-bar panel when an active certification is set.
- Each bar shows: domain name, weight percentage badge (e.g. "28%"), mastery fill (colored), gap (remaining grey fill). Bars appear in `sequence_order` (Domain 1, 2, 3…), not sorted by gap size — practitioners should know which domain is Domain 1, not need to figure it out from sorted bars.
- Source indicator: if any bar has `source = 'self_assessment_estimate'`, show a note below the chart: *"Shaded domains show initial estimates from your self-assessment. Take cert-relevant quizzes to refine them."* Remove the note once all domains have `quiz_derived` scores.
- Tooltip on hover: "Domain X: [name] · [weight]% of exam · Last updated: [date]".
- Fallback: if no certification is set on the active profile, render the original skill-gap bars (top skills by gap score from `skill_profile_snapshots`).

**Scenario tests:**
- *A practitioner with 3 correct cert-evaluated answers in Domain 1 has `mastery_score > 0` for Domain 1 in `certification_domain_scores` after regenerating the path.*
- *A non-cert-evaluated quiz answer (`is_cert_evaluated = false`) does not change any `certification_domain_scores` row.*
- *The `CertDomainGapChart` renders domains in `sequence_order`, not sorted by gap size.*
- *If all domain scores have `source = 'quiz_derived'`, the "initial estimates" note is absent from the chart.*

**Definition of done:** all four pass; `compute_domain_scores` utility has its own unit test; the `CertDomainGapChart` renders correctly for both practitioner and admin views; existing skill-gap chart remains as fallback for no-cert profiles.

---

### Step 10.10 — Quiz UI certification-domain awareness

**Goal:** the quiz experience clearly communicates which questions count toward exam readiness and which are supplementary context. Color-coded tab badges and item-level labels give practitioners informed control over where to focus their session.

**Preconditions:** 10.9.
**Context to load:** `frontend/src/components/QuizRunner/`, Step 6.8 (cert-ordered skill selector, already places cert skills first).

**Build:**

*Frontend:*
- **Skill selector tabs** (extending Step 6.8): add a colored badge to each skill tab that has items tagged `is_cert_evaluated = true` for that skill:
  - Cert-domain skills with exam-relevant items: blue **"Exam"** pill next to the skill name.
  - Skills with only supplementary items (`is_cert_evaluated = false`): grey **"Supplementary"** pill, or no pill if the distinction is already clear from the section divider (UX judgment call).
  - Section divider between cert skills and supplementary skills (already present from Step 6.8) is labeled: **"Exam-critical ↑ · Good to know ↓"**.

- **Item card badges**: each question card shows a small badge at the top-left:
  - `is_cert_evaluated = true` → **"📋 Exam relevant"** (blue/teal background)
  - `is_cert_evaluated = false` → **"💡 Good to know"** (grey background)
  - Tooltip on "Exam relevant": *"Answering this correctly improves your [cert code] [domain name] readiness score."*
  - Tooltip on "Good to know": *"This topic supports understanding but isn't directly evaluated in [cert code]."*

- **Post-answer score-impact note** (shown in the answer reveal / grader result panel):
  - Cert-evaluated correct answer: *"✅ Counts toward your [domain name] readiness score."*
  - Supplementary correct answer: *"ℹ️ Builds your understanding. Doesn't change your exam-domain readiness scores."*

*Backend:*
- Extend the quiz items endpoint response to include `is_cert_evaluated: bool` and `certification_domain_name: str | None` per item, so the frontend can render badges without a separate lookup.

**Scenario tests (Playwright):**
- *A quiz item where `is_cert_evaluated = true` shows a blue "Exam relevant" badge; an item where `is_cert_evaluated = false` shows a grey "Good to know" badge.*
- *After submitting a correct answer for an "Exam relevant" item, the post-answer panel contains the text "Counts toward your" and the domain name.*
- *After submitting a correct answer for a "Good to know" item, the post-answer panel contains "Doesn't change your exam-domain readiness scores".*
- *In dark mode, both badge types remain readable (contrast ≥ 4.5:1 against card background).*

**Definition of done:** all four pass; badge CSS uses design-system tokens, not hardcoded hex colors; the quiz UI works correctly when `certification_domain_id` is NULL (legacy items — show no badge, no post-answer note, no tooltip).

---

### Step 10.11 — Visual mastery trend indicators (↑ green / ↓ amber on radar + domain chart)

**Goal:** every skill row in the Skill Radar and every domain bar in the domain gap chart clearly shows whether it is trending up, down, or stable since the last profiler run — using color and directional labels so a practitioner immediately sees what is improving and what is declining.

**Preconditions:** 10.10 (domain gap chart from Step 10.9 is in place and the quiz UI is complete; `mastery_history` table contains the data to compute deltas; Step 10.7's scoring model provides `previous_mastery_score`).
**Context to load:** Step 10.7 (delta computation), `frontend/src/components/SkillRadar/`, the `CertDomainGapChart` component from Step 10.9.

**Design — three trend states:**

| State | Condition | Color | Label / Icon |
|---|---|---|---|
| Improving | `current > previous + 0.01` | Green | `↑ +X%` |
| Declining | `current < previous − 0.01` | Amber/red | `↓ −X%` |
| Stable | within ±0.01 of previous | Grey | `→ No change` |

A ±1% dead-band prevents cosmetic noise from triggering indicators after rounding. The threshold (0.01) is a named configuration constant, not a magic number.

**Build:**

*Backend:*
- `GET /practitioners/{id}/skill-profile` response: extend the per-skill payload to include:
  - `previous_mastery_score`: float | null — the second-most-recent `mastery_history` row for this skill; null if only one history row exists
  - `mastery_delta`: float | null — `current − previous`, null when no previous
  - `trend`: `"improving"` | `"declining"` | `"stable"` | `"new"` — computed server-side; `"new"` when no previous score exists
- `GET /practitioners/{id}/certification-domain-scores` response (from Step 10.6): extend similarly with `mastery_delta` and `trend` per domain row — domain history is derived from the `certification_domain_scores.last_computed_at` + a new lightweight `certification_domain_score_history` append-only log, or simply the delta between the current row and the previous computed value stored as `previous_mastery_score` on the row itself. Keep it simple: add `previous_mastery_score` as a column on `certification_domain_scores`, updated on each compute pass.
- Both computations are lightweight SQL — no LLM call.

*Frontend — Skill Radar (`SkillRadar` component):*
- Each radar axis / spoke uses the trend color for its label text and filled data point:
  - `improving` → green label and point
  - `declining` → amber/red label and point
  - `stable` / `new` → default theme color, no indicator on `new`
- Delta tag below or beside each axis label: `↑ +12%` or `↓ −8%`. If the chart is too compact, fall back to a legend table below the chart (columns: Skill name | Current | Change | Trend icon). Rows where trend = `declining` get a subtle amber row background.

*Frontend — Domain gap chart (`CertDomainGapChart` component, Step 10.6):*
- Each bar renders a **delta chip** to the right: `+12%` in green, `−8%` in red, or nothing when stable/new.
- Bar fill color follows trend: `declining` → amber/red fill; `improving` → green fill (or green overlay); `stable`/`new` → standard fill.
- Tooltip on hover: "Previous: 58% → Current: 50% (−8%) · Last updated: [date]".

*Theme-awareness:*
- All trend colors must work in both light and dark modes via CSS variables — no hardcoded hex.
- `--color-trend-up`: green token; `--color-trend-down`: amber/red token; `--color-trend-neutral`: muted text token.

**Scenario tests (Playwright):**
- *A practitioner whose mastery on skill X dropped from 70% to 55% after a bad quiz round sees an amber `↓ −15%` indicator on skill X's radar axis — not the default color.*
- *A practitioner whose Domain 2 readiness rose from 40% to 58% sees a green `↑ +18%` delta chip on the Domain 2 bar in the domain gap chart.*
- *A brand-new skill or domain (first time appearing — no previous score) shows no trend indicator, only the current score.*
- *In dark mode, trend colors remain readable (contrast ≥ 4.5:1 against the background).*

**Definition of done:** all four pass; trend color tokens are defined as CSS variables; the delta chip renders correctly on both the radar legend and the domain gap chart in both light and dark mode; `previous_mastery_score` column exists on `certification_domain_scores`.

---

# Phase 11 — Mock Exam System

### Step 11.1 — Exam config data model, migration & seed

**Goal:** every certification carries the three pieces of information needed to administer a properly-scoped mock exam — question count, time limit, and passing threshold — stored in the `certifications` table and populated by the seed script.

**Preconditions:** 10.11.
**Context to load:** `backend/app/db/models.py`, `backend/alembic/versions/015_progressive_scoring.py`, `backend/seed/generate.py`.

**Build:**

*Alembic migration 016:*
- Add to `certifications`: `exam_question_count INTEGER`, `exam_duration_minutes INTEGER`, `exam_passing_score_pct NUMERIC(5,2)`
- Create `mock_exam_sessions`: id PK, practitioner_id FK, certification_id FK, status (in_progress/paused/completed), time_elapsed_seconds, last_resumed_at, score, correct_count, total_count, started_at, completed_at, created_at
- Create `mock_exam_questions`: id PK, session_id FK (CASCADE), sequence_order, certification_domain_name, skill_name, prompt, answer_key JSONB, trap_explanation, difficulty, response JSONB, score, answered_at

*Seed exam configs per cert:*

| Code    | Questions | Duration | Pass % |
|---------|-----------|----------|--------|
| CCAO-F  | 60        | 120 min  | 70.00  |
| CCDV-F  | 60        | 120 min  | 70.00  |
| CCAF    | 60        | 120 min  | 70.00  |
| CCAR-P  | 70        | 150 min  | 75.00  |
| AIF-C01 | 65        | 90 min   | 70.00  |
| MLA-C01 | 65        | 130 min  | 72.00  |
| GCGAIL  | 50        | 120 min  | 70.00  |
| GCPMLE  | 60        | 120 min  | 70.00  |
| AI-900  | 45        | 45 min   | 70.00  |
| AI-102  | 60        | 120 min  | 70.00  |

**Definition of done:** migration applies cleanly; seed writes all three columns for all 10 certs; both new tables exist.

---

### Step 11.2 — MockExamGenerator Agent + mock exam API routes

**Goal:** a practitioner can start a mock exam, answer each question with instant feedback, pause/resume, and complete it. Only one active session at a time. Completion writes adoption-trend records.

**Preconditions:** 11.1.
**Context to load:** `backend/app/agents/base.py`, `backend/app/agents/item_writer.py`, `backend/app/api/routes/learning_paths.py`.

**Build:**

*MockExamGeneratorAgent:* generates hard-difficulty (0.70–1.00) MCQ batches of 15. Input: cert_code, cert_name, batch_size, domain_focus, batch_number. Output: list of question specs (prompt, 4 options, correct_index, trap_index, trap_explanation, difficulty).

*Orchestration:* on POST /mock-exams, run batches concurrently via asyncio.gather (60 questions = 4 parallel calls, each targeting a cert domain proportionally).

*API routes (`mock_exams.py`):*
- POST create (409 if active session exists)
- GET active session (404 if none)
- PATCH pause / resume
- POST answer a question (grade, reveal correct_index + trap; 409 if already answered)
- POST complete (all answered required; write SkillProfileEvents for Adoption Trend)

Security: correct_index excluded from response until question is answered.

**Definition of done:** `py -m pytest` passes; app starts cleanly; mock exam router registered at `/api/v1`.

---

### Step 11.3 — Quiz tab answered-questions log + stable tab ordering

**Goal:** tab ordering never shifts; each tab shows (answered/total) progress; a collapsible "Answered" section below the active question lets practitioners review prior answers.

**Preconditions:** 10.10.
**Context to load:** `frontend/src/components/QuizRunner/QuizRunner.tsx`.

**Build:**
1. Stable tab ordering — cert/supp partition computed once at mount; never re-sorted as attempts arrive
2. Progress badge on each tab: `Skill Name (2/5)` — turns green when fully answered
3. Answered accordion below active question — rows: `[Q3] Correct 85%` or `[Q3] Incorrect 0%`; expand to reveal prompt, chosen answer, correct answer (if wrong), trap explanation
4. Next button skips already-answered items; shows completion message when skill fully answered

**Definition of done:** `npx tsc --noEmit` clean; tabs stable; badge accurate; accordion shows all answered items.

---

### Step 11.4 — Skill Radar 80%-mastery CTA + MockExamPage

**Goal:** practitioners at 80%+ mastery see a "Take a Mock Exam" prompt on the Skill Radar, which opens a full-screen exam in a new browser tab with timer, per-question feedback, pause/resume, and a final score screen.

**Preconditions:** 11.2, 11.3.
**Context to load:** `frontend/src/components/SkillRadar/SkillRadar.tsx`, `frontend/src/App.tsx`, `frontend/src/api/types.ts`, `frontend/src/api/index.ts`, `frontend/src/hooks/index.ts`.

**Build:**
- Types: MockExamQuestion, MockExamSession (with exam_question_count, exam_duration_minutes, exam_passing_score_pct)
- API client: mockExams.start, getActive, pause, resume, answer, complete
- Hooks: useStartMockExam, useActiveMockExam (polls while in_progress), usePauseMockExam, useResumeMockExam, useAnswerMockExamQuestion, useCompleteMockExam
- SkillRadar CTA: when avg mastery >= 80%, show exam-ready card with cert exam metadata + Start/Resume button; opens new tab at /mock-exam/{session_id}; spinner during generation
- MockExamPage (/mock-exam/:sessionId): header with timer (counts up, pauses on pause), question card with 4 options + submit, overview grid (white/green/red squares), answered accordion; paused state shows Resume screen; completion screen shows score + Pass/Fail + "Saved to Adoption Trend"; no browser storage used
- App.tsx: add /mock-exam/:sessionId route

**Definition of done:** `npx tsc --noEmit` clean; exam starts, timer runs, pause/resume works, all questions answerable with feedback, completion confirmed, Adoption Trend shows mock_exam events.

---


# Phase 12 — Quiz Generation: Decoupled, Batched, Fast

## Design rationale

### The bounded nature of quiz questions

A certification path is bounded by its exam blueprint: typically 4–5 official domains,
each covered by 3–4 skills, giving a maximum of ~16 skill nodes.  The Quiz tab needs
**one starter question per skill** — that is both the minimum useful amount and the
correct ceiling.  Generating more questions than this upfront is wasteful; generating
fewer leaves skill tabs empty.

The original design called Item-Writer once per skill during path generation, sequentially.
Sixteen sequential LLM calls at 2–4 minutes each = 32–64 minutes of wall time — far too
slow for what is conceptually a < 30 second "refresh my radar" action.

### Why not batch all questions in a single very large call?

The appeal of generating 5 questions per skill × 16 skills = 80 questions in one call is
understandable, but wrong in two ways:

1. **Scale mismatch.** 80 MCQs at ~500 tokens each = 40,000 output tokens.  Both
   Nemotron and Claude become unreliable at that output size: timeouts, truncation, and
   malformed JSON all increase sharply beyond ~10,000 output tokens.
2. **Purpose mismatch.** The quiz tab is not the mock exam.  The mock exam (Phase 11)
   has 60–70 carefully generated hard questions.  The quiz tab exists to assess mastery
   and generate adaptive practice — one question per skill is the right granularity.
   When the practitioner exhausts a skill's current question, the existing auto-refresh
   path (Step 10.8) generates the next one in the background.

### Why not generate per-skill-tab on demand (Option B from the discussion)?

This appears responsive (first question in ~15 seconds) but merely hides the problem:
16 tabs × 1 call each = 16 sequential calls behind the scenes if the practitioner
browses all tabs.  State management also becomes complex (each tab has an independent
loading state, race conditions on shared cache keys).

### Chosen design — single batch call, all questions at once

| Event | Action | Wall time |
|---|---|---|
| Click "Generate / Regenerate path" | Profiler → Planner → persist; **no Item-Writer** | **< 30 seconds** |
| Click Quiz tab (first open, no items) | Show friendly loading screen; fire **one** QuizBatchGeneratorAgent call covering all skills | **~20–30 seconds** |
| Quiz tab after batch returns | All skill sub-tabs populated simultaneously | **< 1 second** |
| Practitioner exhausts a skill's question(s) | Auto-refresh (Step 10.8): single Item-Writer call for that skill only | **~15–20 seconds** |

One call for 16 questions at 500 tokens each = 8,000 output tokens — well within every
supported model's reliable range and fast enough that a single "Generating your quiz…"
loading screen is acceptable.

---

### Step 12.1 — Decouple ItemWriter from path generation

**Goal:** "Generate Learning Path" completes in under 30 seconds.  No quiz questions are
written during this step; the workflow is Profiler → Domain Score computation → Planner →
persist path + snapshots → done.

**Preconditions:** 11.4.
**Context to load:** `backend/app/workflows/generate_learning_path.py`,
`backend/app/api/routes/learning_paths.py`, `docs/architecture.md`.

**Build:**

*`generate_learning_path.py` — `_run_steps`:*
- Remove the entire Item-Writer block (step 4) and all associated code:
  `ItemWriterAgent`, `ItemWriterInput` imports, the `writer_tasks` list,
  `_run_writer_concurrent`, `_run_writer_sequential`, `asyncio.Semaphore`,
  `items_by_skill` dict, and the `item_id` look-up when writing `LearningPathItem` rows.
- `LearningPathItem.item_id` becomes null on creation (the column is already nullable;
  the auto-refresh workflow (Step 10.8) sets it when the first item is generated).
- Remove `item_writer_session_factory` parameter from `run_generate_learning_path`
  and `_run_steps` — no longer needed.
- Remove `AsyncSessionLocal` import from the workflow.
- Update the docstring: sequence is now Profiler → Domain Scorer → Planner → persist.

*`learning_paths.py` API route:*
- Remove `item_writer_session_factory=AsyncSessionLocal` argument.
- Remove `AsyncSessionLocal` import from this file.

*Scenario test (`test_learning_path_workflow.py`):*
- Rename `test_full_workflow_creates_workflow_run_and_three_agent_runs`
  → `test_full_workflow_creates_workflow_run_and_two_agent_runs`.
- Update stub to provide only 2 side-effects (profiler + planner).
- Assert `agent_runs.count == 2` (was 3).
- Assert that no `items` rows are written.

**Definition of done:** `py -m pytest` green; "Generate path" in the running app
completes and the browser returns control to the user within 90 seconds.

---

### Step 12.2 — QuizBatchGeneratorAgent

**Goal:** a single LLM call generates one well-calibrated starter question for every skill
in the practitioner's active learning path, covering all cert domains proportionally.

**Preconditions:** 12.1.
**Context to load:** `backend/app/agents/base.py`,
`backend/app/agents/item_writer.py` (for AnswerKey / ItemWriterOutput schema),
`backend/app/agents/prompts/item_writer.md`,
`backend/app/api/routes/learning_paths.py`.

**Build:**

*Agent (`backend/app/agents/quiz_batch_generator.py`):*

Input:
```python
class QuizBatchGeneratorInput(BaseModel):
    skills: list[SkillQuizSpec]     # one entry per skill in the path
    cert_code: str
    cert_name: str
    certification_domains: list[dict] | None   # [{id, name, description, weight_pct}]

class SkillQuizSpec(BaseModel):
    skill_id: str
    skill_name: str
    skill_description: str | None
    mastery_score: float            # 0.0–1.0 — drives target difficulty
    certification_domain_id: str | None
    certification_domain_name: str | None
    is_cert_evaluated: bool
    prior_generation_count: int = 0 # how many batches have already been generated
```

Output:
```python
class QuizBatchGeneratorOutput(BaseModel):
    items: list[BatchQuizItem]

class BatchQuizItem(BaseModel):
    skill_id: str
    item_type: str                  # always "mcq"
    prompt: str
    answer_key: AnswerKey           # reuse existing AnswerKey Pydantic model
    trap_explanation: str | None
    difficulty: float               # calibrated to mastery_score band
    certification_domain_id: str | None
    is_cert_evaluated: bool
```

`max_tokens = 12000` (16 items × ~700 tokens each with breathing room).

Prompt file: `backend/app/agents/prompts/quiz_batch_generator.md`

Prompt instructions:
- Generate exactly one MCQ per skill in the `skills` list, in the same order.
- Calibrate difficulty to `mastery_score`:
  - 0–0.25 → target 0.30–0.45 (foundation — build confidence)
  - 0.25–0.55 → target 0.45–0.65 (solidifying — apply concepts)
  - 0.55–0.80 → target 0.65–0.80 (challenge — nuanced scenarios)
  - 0.80–1.00 → target 0.80–0.95 (exam-hard — same bar as mock exam)
- Each question: 4 options, one correct, one plausible trap, a concise trap explanation.
- If `certification_domain_id` is set, the question must directly test the domain concept.
- If `prior_generation_count > 0`, vary the question style from previous rounds
  (use "EXCEPT", "MOST appropriate", "FIRST step", scenario-based formats to avoid
  repeating similar phrasings).
- Output MUST include one item per skill — never skip a skill or add extras.
- Output field: `items` array in the same order as the input `skills` array.

*New endpoint:*

`POST /practitioners/{practitioner_id}/learning-paths/{path_id}/quiz-batch`

In `backend/app/api/routes/learning_paths.py`:
- Require the path to belong to the practitioner; 404 otherwise.
- Fetch all path skills with their current mastery scores from `skill_profile_snapshots`.
- Compute `prior_generation_count` per skill = count of existing `items` rows for that skill.
- Call `QuizBatchGeneratorAgent`.
- Persist each `BatchQuizItem` as an `Item` row (same columns as existing `items` table).
- Update `LearningPathItem.item_id` for each skill to point to the newly created item.
- Return list of created `Item` ids (frontend fetches via existing `useItems` hooks).

**Scenario test:**
```
Scenario: Batch generates exactly one item per skill for the active path
  Given a practitioner with a locked profile and an active learning path of 3 skills
    and no existing items for those skills
  When POST /practitioners/{id}/learning-paths/{path_id}/quiz-batch is called
  Then exactly 3 Item rows are created, one per skill
    and each Item has difficulty calibrated to the skill's mastery_score band
    and each Item is linked to its LearningPathItem via item_id
```

**Definition of done:** scenario test green; a real call to the endpoint produces N items
in the DB in under 60 seconds.

---

### Step 12.3 — Quiz tab loading UX

**Goal:** when the Quiz tab is opened with no items, a friendly loading screen covers the
full quiz panel while the batch endpoint is called; all skill tabs populate simultaneously
when the call returns; the loading state is isolated from the rest of the dashboard.

**Preconditions:** 12.2.
**Context to load:** `frontend/src/components/QuizRunner/QuizRunner.tsx`,
`frontend/src/api/index.ts`, `frontend/src/hooks/index.ts`.

**Build:**

*`api/index.ts`:*
```typescript
generateQuizBatch: (practitionerId: string, pathId: string) =>
  api.post<{ item_ids: string[] }>(
    `/practitioners/${practitionerId}/learning-paths/${pathId}/quiz-batch`,
    {}
  ),
```

*`hooks/index.ts`:*
```typescript
export function useGenerateQuizBatch(practitionerId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (pathId: string) =>
      practitioners.generateQuizBatch(practitionerId, pathId),
    onSuccess: () => {
      // Invalidate all items queries so skill tabs re-fetch
      qc.invalidateQueries({ queryKey: ["items"] });
    },
  });
}
```

*`QuizRunner.tsx` — batch-loading gate:*

At the top of the quiz panel, before rendering skill tabs, check whether any skill in the
path has items.  If NO skill has items AND the active path exists:

1. Auto-trigger `useGenerateQuizBatch(practitionerId).mutate(activePath.id)` once on mount
   (guard with a `useEffect` + `hasTriggered` ref to fire exactly once).
2. While the mutation is pending, render a full-panel loading screen:
   ```
   ┌────────────────────────────────────────────────────────┐
   │                                                        │
   │   ☕  Generating your quiz — one moment               │
   │                                                        │
   │   We're crafting one question per skill,               │
   │   calibrated to your current mastery level.           │
   │                                                        │
   │   ████████████░░░░░░░░░░  preparing 16 questions…     │
   │   (indeterminate progress bar)                         │
   │                                                        │
   └────────────────────────────────────────────────────────┘
   ```
   The message shows `activePath.items.length` as the question count.
3. On success: `queryClient.invalidateQueries` causes all `useItems(skillId)` hooks
   to refetch → skill tabs populate with their questions automatically.
4. On error: show inline error card with "Retry" button that calls mutate again.

*No changes to the per-skill auto-refresh path* (Step 10.8) — that already shows a
per-skill loading skeleton when a new single question is being generated.

**Scenario tests:** none (visual component — TypeScript compile is the gate).
**Definition of done:** `npx tsc --noEmit` clean; opening the Quiz tab on a fresh path
triggers exactly one batch call; all skill tabs are populated when it returns; a Retry
button appears on network failure; revisiting the tab (items already in DB) renders
immediately with no loading screen.

---


# Phase 13 — Dynamic Cert Skill Discovery & Domain-Weighted Radar

## Design rationale

### Why cert skills cannot be seeded

The five skills currently seeded for CCAR-P (`Orchestration Patterns`, `Agent Observability`,
`MCP Servers`, `Model Deployment`, `Monitoring & Drift Detection`) reflect a point-in-time
interpretation of the exam blueprint, not the authoritative blueprint text.  Three structural
problems make this approach unsustainable:

1. **Staleness.** Anthropic, AWS, and other providers revise exam content quarterly to yearly.
   Skill weights and knowledge areas shift between versions; a seed file can only capture a
   snapshot.  There is no practical way to keep it fresh without agent-driven discovery.
2. **Sparseness.** Five skills for five domains is a 1:1 mapping.  An official exam blueprint
   describes each domain through three to five distinct knowledge areas.  Ten to twelve skills
   covering all domains gives the Curriculum Planner enough signal to build a differentiated,
   exam-representative learning path and gives practitioners meaningful skill-level visibility
   into each domain — not just domain-level aggregates.
3. **Catalog pollution.** The Curriculum Planner draws from the full `skills` catalog, which
   contains generic foundational skills shared across all certs (Prompt Engineering, AI
   Foundations, etc.).  Without a clear cert-specific skill set, the planner pads paths with
   generic skills that don't move exam-domain readiness scores — producing the "all SUPP" tabs
   observed before Phase 12.3.

### The fix: research at cert selection time

A **CertSkillMapperAgent** runs web search against the certification's current exam guide and
returns 10–12 overarching skills that collectively cover all exam domains.  Each skill is linked
to the domain it primarily belongs to, inheriting that domain's weight.  Skills are cached per
certification × domain-version in `certification_skills` — one agent call serves every practitioner
targeting that cert under that domain version.

The result replaces the sparse, seed-only skill set with a current, comprehensive, domain-aligned
one without requiring a code change or redeploy when a cert provider revises their blueprint.

### Why domain-colored radar nodes

Currently radar nodes are monochrome — a practitioner cannot tell at a glance which skills are
exam-critical vs. supplementary, or which domains carry the most weight.  Coloring nodes by domain
weight communicates priority visually: a skill belonging to the 25% domain gets a more intense
color than one in the 15% domain.  A tooltip surfaces the domain name and weight on hover.
Supplementary (non-cert) skills remain neutral grey — clearly secondary without being hidden.

### 80/20 quiz split

The curriculum planner's `supp_max` formula (`max(1, round(len(cert_skills) × 0.2))`) already
enforces the structural constraint.  With 10–12 cert skills, `supp_max` yields 2 supplementary
slots — 10/(10+2) = 83%, 12/(12+2) = 86% — both above the 80% floor.  Phase 13 makes the floor
explicit and auditable: the QuizBatchGeneratorAgent logs the cert/supp ratio on every call and
warns (without blocking) if it falls below 80%, so any regression in path composition is visible
in the observability dashboard.

---

### Step 13.1 — DB schema: extend `certification_skills` with domain linkage and source provenance

**Goal:** every `certification_skills` row knows which exam domain the skill primarily belongs to
and whether it was seeded manually or discovered by the agent.

**Preconditions:** 12.3.
**Context to load:** `docs/data-model.md`, `backend/app/db/models.py`, latest Alembic migration.

**Build:**

*New Alembic migration:*
- `certification_skills.certification_domain_id` (FK → `certification_domains`, nullable ON DELETE
  SET NULL) — the exam domain this skill primarily maps to within the cert.  Null for seed rows
  that predate Phase 13; always populated for agent-discovered rows.
- `certification_skills.source` (text, NOT NULL, `server_default='seed'`) — provenance:
  `'seed'` for bootstrap data written in migrations/seed files; `'agent_discovered'` for rows
  written by CertSkillMapperAgent.

*SQLAlchemy model (`CertificationSkill`):*
- Add `certification_domain_id: Mapped[str | None]` with FK to `certification_domains`.
- Add `source: Mapped[str]` with `server_default="seed"`.

Run `alembic upgrade head` immediately after writing the migration.

**Definition of done:** `py -m pytest` green; migration applies cleanly; `CertificationSkill`
model has both new fields; existing seed rows have `source = 'seed'` and
`certification_domain_id = NULL`.

---

### Step 13.2 — CertSkillMapperAgent 👤

**Goal:** an agent that web-searches the certification's current exam guide and returns 10–12
overarching skills aligned to the cert's official exam domains.  Skills are upserted into
`certification_skills` (and `skills` if new) with domain linkage and `source='agent_discovered'`.

**Preconditions:** 13.1.
**Context to load:** `backend/app/agents/base.py`,
`backend/app/agents/cert_domain_discovery.py` (web-search pattern),
`backend/app/db/models.py`, `docs/architecture.md`.

**Build:**

*Agent (`backend/app/agents/cert_skill_mapper.py`):*

Input:
```python
class CertSkillMapperInput(BaseModel):
    cert_code: str                       # e.g. "CCAR-P"
    cert_name: str                       # e.g. "Claude Certified Architect – Professional"
    cert_external_url: str | None        # official exam guide URL if known
    domains: list[CertSkillMapperDomain]

class CertSkillMapperDomain(BaseModel):
    domain_id: str
    domain_name: str
    domain_description: str
    weight_pct: float                    # e.g. 25.0 for the 25% domain
```

Output:
```python
class CertSkillMapperOutput(BaseModel):
    cert_code: str
    skills: list[DiscoveredCertSkill]    # 10–12 items
    source_notes: str                    # URLs consulted, confidence notes, date verified
    confidence: str                      # "high" | "medium" | "low"

class DiscoveredCertSkill(BaseModel):
    skill_name: str
    skill_description: str               # 1-2 sentences; what a practitioner must know/do
    primary_domain_id: str               # must match one of the input domain_ids
    weight: float                        # 0.0–1.0; prominence within that domain
    rationale: str                       # one sentence: why this skill for this cert/domain
```

Prompt file: `backend/app/agents/prompts/cert_skill_mapper.md`

Prompt contract (exact wording is the 👤 task — see `docs/human-in-the-loop.md`):
- Search for "[cert_name] exam guide", "[cert_code] exam blueprint", "[cert_name] official
  certification topics".  Prefer the cert provider's official page over third-party study sites.
- Return exactly 10–12 skills; fewer only when evidence is genuinely insufficient
  (set `confidence = "low"` and explain).  Never invent skills not supported by evidence.
- Map each skill to exactly one of the provided domain IDs (primary domain).
- Weight each skill 0.3–1.0 based on its prominence in the exam guide.
- Name skills at the right granularity: not too broad ("AI Systems"), not too narrow
  ("Implementing a timeout on tool call retries").  Aim for knowledge areas a practitioner
  can train on and a quiz can test.
- If the exam guide cannot be found, set `confidence = "low"`, name what was found and what
  was not, and still provide the best-effort skill list from the domain descriptions provided.

*Skill upsert service (`backend/app/services/cert_skill_mapper_service.py`):*
```python
async def persist_cert_skill_mapping(
    cert_id: str,
    agent_run_id: str,
    output: CertSkillMapperOutput,
    db: AsyncSession,
) -> dict:
    # 1. Resolve or create each skill in `skills` table (match by name, case-insensitive).
    # 2. Delete existing agent_discovered rows for this cert (keeps seed rows intact).
    # 3. Insert new CertificationSkill rows:
    #    source='agent_discovered', certification_domain_id set, weight from output.
    # 4. Return {skills_created, skills_matched, confidence}.
```

*Admin endpoint:*
`POST /admin/certs/{cert_id}/discover-skills`
- Fetches current domain version for the cert; builds `CertSkillMapperInput`.
- Calls CertSkillMapperAgent.
- Persists results via `persist_cert_skill_mapping`.
- Returns `{skills_created, skills_matched, source_notes, confidence}`.

*Scenario tests:*
```
Scenario: Agent maps 10 discovered skills to cert domains
  Given a cert with 5 domains and a stub CertSkillMapper response of 10 skills
  When POST /admin/certs/{cert_id}/discover-skills is called
  Then 10 certification_skills rows exist with source='agent_discovered'
    and each row has a non-null certification_domain_id matching one of the cert's domains
    and the skills table has rows for each discovered skill name

Scenario: Re-running discovery replaces previous agent_discovered skills
  Given 10 existing agent_discovered skills for a cert
  When POST /admin/certs/{cert_id}/discover-skills is called again with a 12-skill response
  Then exactly 12 agent_discovered rows exist (old 10 replaced)
    and seed rows (source='seed') are untouched
```

**Definition of done:** 👤 `agents/prompts/cert_skill_mapper.md` written (prompt, confidence
vocabulary, failure-mode instructions); scenario tests green; admin endpoint returns correct
skill count and source notes; CCAR-P discovery returns 10–12 meaningful skills in a live test.

---

### Step 13.3 — Profile creation hook: trigger skill mapping at profile lock time

**Goal:** when a practitioner locks their profile, the system ensures CertSkillMapperAgent has
run for that cert.  If not, it runs (with a 60 s timeout) before returning — so the first
`generate_learning_path` call always operates on the full 10–12-skill set.

**Preconditions:** 13.2.
**Context to load:** `backend/app/api/routes/profiles.py`,
`backend/app/workflows/generate_learning_path.py`, `backend/app/db/models.py`.

**Build:**

*Profile lock endpoint:*

After the existing Domain Scorer Agent call, add:
```python
# Phase 13.3: ensure cert has agent-discovered skills before path generation.
from sqlalchemy import func as sql_func
skill_count_result = await db.execute(
    select(sql_func.count()).select_from(CertificationSkill).where(
        CertificationSkill.certification_id == profile.certification_id,
        CertificationSkill.source == "agent_discovered",
    )
)
if skill_count_result.scalar() == 0:
    try:
        await asyncio.wait_for(
            run_cert_skill_mapping(profile.certification_id, db, claude_client),
            timeout=60.0,
        )
    except asyncio.TimeoutError:
        logger.warning(
            "CertSkillMapper timed out for cert %s — using seed skills for first path",
            profile.certification_id,
        )
```

*`generate_learning_path.py`:*

When resolving `cert_goal_context`, prefer `agent_discovered` certification_skills rows; fall
back to `seed` rows if none exist.  Add a `selectinload` filter or a second query:
```python
# Prefer agent_discovered skills; fall back to seed if none.
cert_skills_query = select(CertificationSkill).where(
    CertificationSkill.certification_id == cert.id,
    CertificationSkill.source == "agent_discovered",
)
discovered = (await db.execute(cert_skills_query)).scalars().all()
cert_skills_to_use = discovered if discovered else cert.certification_skills
```

**Scenario test:**
```
Scenario: Profile lock triggers skill mapping when no agent-discovered skills exist
  Given a practitioner with a profile targeting CCAR-P
    and 0 agent_discovered certification_skills for CCAR-P
    and a stub CertSkillMapper response of 10 skills
  When POST /profiles/{id}/lock is called
  Then 10 certification_skills rows exist with source='agent_discovered'
    and the lock response returns HTTP 200

Scenario: Profile lock skips skill mapping when agent_discovered skills already exist
  Given 10 existing agent_discovered skills for CCAR-P
  When POST /profiles/{id}/lock is called
  Then no additional CertSkillMapper agent_runs row is created
```

**Definition of done:** `py -m pytest` green; profile lock calls the mapper when needed; a
60 s timeout does not fail the lock; `generate_learning_path` prefers agent-discovered skills.

---

### Step 13.4 — Domain-weighted Skill Radar

**Goal:** radar nodes are colored by the weight of the exam domain they primarily belong to.
High-weight domains show intense, saturated color; lower-weight domains show lighter variants.
Supplementary skills (no domain) use neutral grey.  A domain legend appears below the radar.

**Preconditions:** 13.3.
**Context to load:** `backend/app/api/routes/skill_radar.py` (or whichever route serves
skill-profile snapshots), `frontend/src/components/SkillRadar/SkillRadar.tsx`.

**Build:**

*Backend — enrich snapshot response:*

Add per-skill domain fields to the snapshot list response:
```json
{
  "skills": [
    {
      "skill_id": "...",
      "skill_name": "...",
      "mastery_score": 0.62,
      "certification_domain_id": "...",
      "certification_domain_name": "Advanced Agentic Systems at Scale",
      "domain_weight_pct": 25.0
    }
  ]
}
```

Implementation: join `CertificationSkill` (source='agent_discovered' preferred, then 'seed')
→ `CertificationDomain` when the active profile has a `certification_id`.  Null domain fields
for supplementary skills.

*Frontend — domain-weight color scale:*

- Collect distinct domains with their `domain_weight_pct`, sort descending by weight.
- Assign each domain a sequential blue hue scaled by weight rank (highest weight → darkest
  blue `#1a56db`, lowest → muted `#93c5fd`).
- Supplementary skills (null domain) → neutral grey `#9ca3af`.
- Apply the color to the radar polygon vertex fill and the tab pill in the Quiz Runner.
- Domain legend below the radar: one row per domain — color swatch, domain name, weight %.
- Tooltip on node hover: `"<skill_name> — <domain_name> (<weight>%)"`.

When no agent-discovered skills exist for the cert (pre-13.2 or mapper hasn't run yet):
radar remains monochrome — no broken UI.

**Definition of done:** `npx tsc --noEmit` clean; CCAR-P radar shows 5 distinct domain colors
(proportional intensity); supplementary skills grey; domain legend visible; tooltip correct;
radar is monochrome when no domain data is available.

---

### Step 13.5 — 80/20 enforcement audit in QuizBatchGeneratorAgent

**Goal:** make the 80/20 cert/supp quiz ratio explicit, logged, and visible in the API response.
The quiz batch endpoint warns (without blocking) when cert-evaluated items fall below 80%.

**Preconditions:** 13.4.
**Context to load:** `backend/app/agents/quiz_batch_generator.py`,
`backend/app/api/routes/learning_paths.py`.

**Build:**

*`quiz_batch_generator.py` — extended output:*
```python
class QuizBatchGeneratorOutput(BaseModel):
    items: list[BatchQuizItem]
    cert_question_pct: float     # e.g. 83.3 for 10 cert / 12 total
    supp_question_pct: float     # e.g. 16.7
```

Compute after generating `items`:
```python
cert_count = sum(1 for i in items if i.is_cert_evaluated)
total = len(items)
cert_pct = round(cert_count / total * 100, 1) if total else 0.0
```

*`learning_paths.py` quiz-batch endpoint:*

After calling the agent:
```python
if output.cert_question_pct < 80.0:
    logger.warning(
        "Quiz batch path=%s cert_pct=%.1f%% (< 80%% target). "
        "cert=%d supp=%d total=%d. Check curriculum planner supp_max.",
        path_id, output.cert_question_pct, cert_count,
        total - cert_count, total,
    )
```

Include `cert_question_pct` and `supp_question_pct` in the JSON response body so the
observability dashboard can surface ratio anomalies without log diving.

*Scenario test:*
```
Scenario: Batch endpoint logs warning when cert ratio falls below 80%
  Given a learning path with 5 cert skills and 5 supp skills
    and a stub QuizBatchGenerator response with 50% cert items
  When POST /learning-paths/{id}/quiz-batch is called
  Then a WARNING log entry is emitted containing "< 80% target"
    and the response returns HTTP 200 with all 10 items
    and cert_question_pct equals 50.0 in the response body
```

**Definition of done:** `py -m pytest` green; `cert_question_pct` and `supp_question_pct`
present in quiz-batch response; warning logged (not raised) when ratio < 80%; CCAR-P path
with 10 agent-discovered skills yields cert_pct ≥ 80% in a live smoke test.

---

# Phase 17 — Continuous Quiz: Progressive Per-Skill Background Generation

**Why this phase exists.** After generating a learning path, practitioners want to see quiz
questions immediately — not after another 30-second wait. At the same time, generating
10–12 full MCQs (with rationales) in a single LLM call produces ~8-12K output tokens,
which consistently exceeds NVIDIA's timeout budgets even after tuning. The fix decouples
generation from the HTTP response: the path response returns immediately; a FastAPI
background task then generates questions **one skill at a time**, each call producing
1-2 questions (~700-1400 tokens) — well within NVIDIA's 90-second window. Questions
appear in the Quiz tab as they finish, with a per-skill "preparing" indicator for skills
not yet ready.

**Design constraint — provider priority:** NVIDIA is always the primary provider.
Anthropic Haiku is only invoked as a fallback when all NVIDIA tiers fail for a given skill.
This is non-negotiable for cost control.

**Rules:**
- 10–12 questions total per round, 1 or 2 per skill (random), cert-evaluated skills
  prioritised for 2-question slots.
- All questions include `correct_rationale` + `incorrect_rationale` (Phase 16 format).
- No question text may be repeated across generations (no-repeat constraint in prompt).
- Per-skill generation errors are **logged and skipped** — one bad skill does not abort
  the rest of the batch.

**Two generation triggers (only two):**

Stage 1 — `POST /learning-paths/generate` called and **no items exist** for the new
path's skills → start background generation immediately after path workflow completes.

Stage 2 — `POST /learning-paths/generate` called again (path regeneration) → check if ALL
existing items for the path's skills have been attempted by this practitioner.
- All answered → start background generation with difficulty adjustment per skill:
  avg_score ≥ 1.0 → push mastery up 0.25 (harder); avg_score < 0.5 → push mastery down
  0.10 (easier); else keep.
- Some unanswered → skip quiz generation entirely, just return the updated path
  (`quiz_skipped_reason = "unanswered_items"`).

**Preconditions:** Phase 16 Definition of Done is met.

---

### Step 17.1 — Schema extension ✅

Add `quiz_generating: bool = False` and `quiz_skipped_reason: str | None = None` to
`GenerateLearningPathResponse` in `backend/app/schemas/learning_paths.py`.
`quiz_generating=True` means a background task was launched; it says nothing about whether
generation has completed.

### Step 17.2 — SkillQuizSpec extension ✅

Add `question_count: int = Field(1, ge=1, le=2)` and `prior_prompts: list[str] = Field(default_factory=list)` to `SkillQuizSpec` in `quiz_batch_generator.py`. Update `_build_messages` to include both fields in the per-skill spec dict and update the user message to say "total items expected = {sum(s.question_count for s in input.skills)}". Update the agent docstring.

### Step 17.3 — Prompt update ✅

Update `backend/app/agents/prompts/quiz_batch_generator.md`:
- Replace "exactly one MCQ per skill" coverage rules with per-spec `question_count` rules.
- Add no-repeat constraint section using `prior_prompts`.
- Update output format example to show a skill with `question_count=2` producing two items.
- Ensure Phase 16 `correct_rationale` / `incorrect_rationale` fields are documented.

### Step 17.4 — Route helpers ✅

Add three helpers to `backend/app/api/routes/learning_paths.py` (before the routes):
- `_check_quiz_exhaustion(practitioner_id, skill_ids, db)` → `(should_generate, is_first_time)`
- `_compute_skill_avg_scores(practitioner_id, skill_ids, db)` → `dict[skill_id, avg_score]`
- `_assign_question_counts(skill_specs, target_min=10, target_max=12)` → None (mutates in-place)

### Step 17.5 — DB migration: `quiz_status` on `learning_path_items`

Add `quiz_status VARCHAR(20) NOT NULL DEFAULT 'pending'` to `learning_path_items`.

| Value | Meaning |
|---|---|
| `pending` | Background task has not yet attempted this skill (or path was just created) |
| `ready` | Agent call succeeded; items are in the `items` table for this skill |
| `failed` | Agent call exhausted all provider tiers; no items were written for this skill |

Alembic migration file: `backend/alembic/versions/018_learning_path_item_quiz_status.py`.

### Step 17.6 — Background generation engine

Add `_generate_quizzes_progressively` as a top-level async function in `learning_paths.py`.

```
_generate_quizzes_progressively(
    practitioner_id: str,
    learning_path_id: str,           # needed to update quiz_status on learning_path_items
    skill_specs: list[SkillQuizSpec],
    cert_code: str,
    cert_name: str,
    certification_domains: list[dict] | None,
    max_gen_by_skill: dict[str, int],
) -> None
```

Behaviour:
- Opens a **fresh `AsyncSession`** (the request session is closed the moment the HTTP response is sent).
- Iterates `skill_specs` in order. For each skill:
  1. Call `QuizBatchGeneratorAgent` with `skills=[spec]` (single-skill, 1–2 questions, ~700–1400 output tokens).
  2. **Success**: persist items, then set `learning_path_items.quiz_status = 'ready'` where `learning_path_id=X` and `skill_id=Y`. Commit.
  3. **Exception** (including `AllProvidersUnavailableError`): set `quiz_status = 'failed'`, log a `WARNING` with the error, commit, continue to the next skill.

`QuizBatchGeneratorAgent.max_tokens` is reduced to 3000 at step 17.11.

### Step 17.7 — `POST /learning-paths/generate` route update

After calling `run_generate_learning_path`:

1. Fetch the new path's `learning_path_id` and skill IDs.
2. Call `_check_quiz_exhaustion` and `_assign_question_counts`.
3. Build the full `skill_specs` list (cert context, prior prompts, difficulty adjustment).
4. If generation is needed: add `_generate_quizzes_progressively(...)` to FastAPI `BackgroundTasks`. Path item rows are already at `quiz_status='pending'` (the default). Return `GenerateLearningPathResponse(quiz_generating=True)` **immediately**.
5. If skipped: return with `quiz_skipped_reason`.

Response time drops from 165 s (3-tier timeout wall) + quiz time back to ~30 s (profiler + planner only).

### Step 17.8 — `POST /quiz-batch` — admin/recovery wrapper

Refactor to call `_generate_quizzes_progressively` synchronously (awaited) for operator-triggered rebuilds. Docstring: "Admin/manual endpoint — normal trigger is POST /learning-paths/generate (background task)."

### Step 17.9 — Retry endpoint

```
POST /practitioners/{practitioner_id}/quiz-generation/retry
```

Logic:
1. Fetch the practitioner's active learning path.
2. Select all `learning_path_items` where `quiz_status = 'failed'` for that path.
3. If none: return `{"retried": 0, "detail": "no failed skills to retry"}` (idempotent noop).
4. Reset each failed item to `quiz_status = 'pending'`.
5. Build `SkillQuizSpec` list for only the failed skills (same helper as 17.7 — cert context, prior prompts, difficulty).
6. Fire `_generate_quizzes_progressively(...)` as a background task.
7. Return `{"retried": N}` immediately.

No auth change needed — enforce `self_or_admin` as with other practitioner endpoints.

### Step 17.10 — Frontend three-state quiz tab

The quiz tab fetches two things on a 5-second poll:
- `GET /items?practitioner_id={id}` — to know which skills have items
- The active learning path — to know each skill's `quiz_status` from `learning_path_items`

Per-skill states (derive from both sources):

| State | Condition | Tab appearance |
|---|---|---|
| **Ready** | items exist for this skill | normal color, questions rendered |
| **Pending** | `quiz_status='pending'`, no items | ⏳ dimmed; "Questions being prepared…" |
| **Failed** | `quiz_status='failed'`, no items | ⚠️ amber; "Generation failed for this skill" |

**"↻ Retry Failed Skills" button** — displayed at the top of the skill-tab group when one or more skills are in `failed` state. Clicking it calls `POST /practitioners/{id}/quiz-generation/retry`, then immediately invalidates the items and path queries to pick up the new `pending` statuses.

Stop polling when every skill is either `ready` or `failed` (no more `pending` skills).

Changes:
- `useGenerateLearningPath.onSuccess` — already invalidates `["items"]`; also invalidate `["learning-path"]` to get fresh `quiz_status` values.
- `QuizRunner` — replace the single ⏳/ready binary with the three-state logic above; add `useRetryQuizGeneration` mutation calling the retry endpoint.

### Step 17.11 — Reduce `QuizBatchGeneratorAgent.max_tokens`

Change from 12000 to 3000. One skill per call = max 2 questions × ~700 tokens ≈ 1400 tokens. 3000 gives safe headroom without telling NVIDIA to reserve compute time for tokens that will not be produced.

### Step 17.12 — Scenario tests

New file `tests/scenarios/test_phase17b_progressive_quiz.py`:

- *Background task invoked* — `POST /learning-paths/generate` with stub, `BackgroundTasks.add_task` called with `_generate_quizzes_progressively`; response has `quiz_generating=True`.
- *Per-skill generation succeeds* — 3 specs, stub client, 3 `db.add(Item)` calls + 3 `quiz_status='ready'` updates.
- *Per-skill failure is isolated* — second skill raises `AllProvidersUnavailableError`; first and third items persisted; second skill's `quiz_status='failed'`; only a WARNING logged; function returns normally.
- *Retry re-queues only failed* — Given path with 2 ready + 1 failed skill, `POST .../retry` resets 1 skill to `pending`, fires background task with 1 spec, returns `{"retried": 1}`.
- *Retry is idempotent* — Given no failed skills, retry returns `{"retried": 0}` and does not fire a background task.
- *Exhaustion skip* — unanswered items exist → `quiz_generating=False`, `quiz_skipped_reason="unanswered_items"`.
- *Difficulty adjustment on refresh* — all answered, one skill avg ≥ 1.0 → mastery pushed up 0.25 in the spec.

### Step 17.13 — Documentation freeze

Update `docs/architecture.md` quiz section and `docs/data-model.md` `learning_path_items` row.

**Definition of done:**
```
py -m pytest tests/scenarios/test_phase17_quiz_generation.py \
             tests/scenarios/test_phase17b_progressive_quiz.py \
             tests/scenarios/test_quiz_batch_ratio.py \
             tests/scenarios/test_phase16_instant_mcq_grading.py -q
```
All pass. Full suite `py -m pytest tests/scenarios/ -q --tb=short` passes.
`POST /learning-paths/generate` returns in under 35 s with `quiz_generating: true`.
Quiz tab shows three distinct states (ready / pending / failed) without a full-screen loading blocker.
`POST .../retry` re-queues only failed skills and returns immediately.
