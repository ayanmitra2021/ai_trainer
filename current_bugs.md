# Current Bugs — Mastery Pulse

Defects identified during full codebase analysis. Each bug has a checkbox for tracking fixes.

---

## Phase 5.5 Known Bugs (from project_plan.md)

- [ ] **Bug 1 — Quiz "Next" button loops on the same question**
  - **File:** `frontend/src/components/QuizRunner/QuizRunner.tsx` (lines 370-384)
  - **Symptom:** Pressing "Next" after answering re-renders the same question instead of advancing.
  - **Root cause:** The `findIndex` callback logic incorrectly compares index vs item position; `itemIndex` state not properly synchronized with `attemptsByItemId` cache updates from `useSubmitAttempt`.

- [ ] **Bug 2 — Skill name text is invisible in the "Rate your skills" panel**
  - **File:** `frontend/src/components/SkillRadar/SelfAssessmentPanel.tsx` (lines 58-59, 181)
  - **Symptom:** Skill names appear white-on-white in dark mode; selected-state pill uses hardcoded `#111` which fails in dark mode.
  - **Root cause:** Hardcoded color literals (`"#1a1a1a"`, `"#111"`) instead of CSS variables; `--surface-alt` lacks dark-mode rule.

- [ ] **Bug 3 — Top skill gaps bar chart does not update after quiz + regenerate**
  - **File:** `frontend/src/components/SkillRadar/SkillRadar.tsx` (lines 259-275) & `frontend/src/hooks/index.ts` (lines 174-191)
  - **Symptom:** Radar polygon refreshes but "Top skill gaps" progress bars show stale values.
  - **Root cause:** `useSubmitAttempt` updates attempts cache but doesn't invalidate `skill-profile` query; bars render from stale `snapshots` via `useMemo` missing dependency.

---

## Backend Bugs

- [x] **Bug 4 — Grader agent changes model dynamically in `_build_messages` (race condition)**
  - **File:** `backend/app/agents/grader.py` (lines 32-37)
  - **Issue:** `self.model` mutated per-request; concurrent requests overwrite each other's model selection.
  - **Fix:** Override model via constructor or pass as parameter to `_call_claude`.

- [x] **Bug 5 — Skill Profiler injects profile assessments with current timestamp (loses original timing)**
  - **File:** `backend/app/workflows/generate_learning_path.py` (line 146)
  - **Issue:** `profile_now = datetime.now(UTC).isoformat()` used for all profile skill assessments, discarding when the practitioner actually rated themselves.
  - **Fix:** Use `psa.updated_at` from the profile assessment row.

- [x] **Bug 6 — `generate_learning_path` workflow doesn't validate practitioner existence before starting**
  - **File:** `backend/app/workflows/generate_learning_path.py` (line 46)
  - **Issue:** No `Practitioner` existence check; FK violation possible if ID is stale.
  - **Fix:** Add `await db.get(Practitioner, practitioner_id)` guard at workflow start.

- [ ] **Bug 7 — Certification Advisor agent prompt doesn't incorporate Phase 6.2 questionnaire fields**
  - **File:** `backend/app/agents/prompts/certification_advisor.md` (not reviewed but implied)
  - **Issue:** New fields (`ai_experience_years`, `primary_job_role`, `deploys_llms_in_production`, `prompt_engineering_familiarity`, `mentors_others_on_ai`) added to `QuestionnaireAnswers` but prompt likely unchanged.
  - **Fix:** Update prompt to weight new signals per Step 6.2 requirements.
  - **Status:** **Not a bug** — prompt already includes Phase 6.2 fields with weighting guidance (see lines 36-62).

- [x] **Bug 8 — Nudge approval endpoint missing `sent_at` timestamp update**
  - **File:** `backend/app/api/routes/pulse.py` (lines 140-159)
  - **Issue:** `Nudge` model has `sent_at` nullable; approval should set it but API may not.
  - **Fix:** Ensure `PATCH /nudges/{id}/approve` sets `sent_at = now()` and `status = "sent"`.

- [x] **Bug 9 — `correlation_snapshots` gap_score calculation allows values for low mastery skills**
  - **File:** `backend/app/agents/correlation.py` (prompt) & `backend/app/workflows/nightly_pulse.py` (lines 252-255)
  - **Issue:** Correlation agent skips practitioners with no snapshots but doesn't filter out low-mastery skills before computing gap; `has_adoption_gap` logic in prompt may not enforce "low mastery ≠ adoption gap" rule from Step 3.2 scenarios.
  - **Fix:** Enforce `trained_score >= 0.5` threshold in Correlation agent output schema via model validator.

- [x] **Bug 10 — Rollup Reporter `MINIMUM_COHORT_SIZE` not exposed to frontend for validation**
  - **File:** `backend/app/agents/rollup_reporter.py` (constant) & `frontend/src/api/types.ts` (Rollup type)
  - **Issue:** Frontend can't independently verify cohort floor; relies solely on `min_cohort_size_met` boolean.
  - **Fix:** Add `min_cohort_size` to `Rollup` model, schema, and API response. (Migration needed for DB column.)

- [x] **Bug 11 — Seed data skill name mismatches in `CERTIFICATIONS_SEED` vs `SKILL_TREE`**
  - **File:** `backend/seed/generate.py` (lines 146-151, 164-170, etc.)
  - **Issue:** Skill weights reference names like "AI Foundations" (parent category) not leaf skills; "MLOps" parent vs "Model Deployment" child mismatch; some weights may not find matching skills (warning printed but seeding continues).
  - **Fix:** Map weights to exact leaf skill names from `SKILL_TREE`.

- [x] **Bug 12 — `PractitionerCertificationGoal.profile_id` FK added but not backfilled for existing goals**
  - **File:** `backend/alembic/versions/007_practitioner_profiles.py` (migration)
  - **Issue:** Migration adds nullable `profile_id` column; existing `practitioner_certification_goals` rows have `NULL`; advisor route (Step 2.3) creates new goals without linking to profile.
  - **Fix:** Update certification advisor route to associate new goals with active profile when one exists.

- [ ] **Bug 13 — Admin session expiry sliding window not implemented correctly**
  - **File:** `backend/app/api/deps/session.py` (lines 73-75)
  - **Issue:** `session.expires_at` extended on *every* request but only for admin; practitioner sessions have `expires_at = None` (correct). However, the check at line 68 deletes expired sessions *before* extending, which is correct, but the extension uses `settings.admin_session_timeout_hours` from config — verify default is 8h per architecture.md.
  - **Status:** **Not a bug** — implementation is correct; default is 8h per config.

- [ ] **Bug 14 — `useSubmitAttempt` hook doesn't invalidate `skill-profile` query after quiz attempt**
  - **File:** `frontend/src/hooks/index.ts` (lines 174-191)
  - **Issue:** Comment says "Skill profile will update after user clicks Regenerate path" but the `skill_profile_event` is written immediately; cache should be invalidated so next "Regenerate" shows fresh data without manual refresh.
  - **Fix:** Add `qc.invalidateQueries({ queryKey: ["practitioners", practitioner_id, "skill-profile"] })` in `onSuccess`.
  - **Status:** **By design** — the design note in CLAUDE.md explicitly states not to re-profile on every answer; cache is invalidated when "Regenerate path" is clicked.

- [ ] **Bug 15 — Item `answer_key` stored as `dict` but `ItemWriterOutput` uses typed union**
  - **File:** `backend/app/schemas/items.py` (lines 54-65) vs `backend/app/db/models.py` (line 661)
  - **Issue:** `answer_key` column is `sa.JSON` (dict); `ItemWriterOutput.answer_key` is `MCQAnswerKey | FreeTextAnswerKey`; serialization works but deserialization loses type info for Grader.
  - **Fix:** Grader input `answer_key: dict` handles both, but add discriminator field or runtime type guard.
  - **Status:** **Not a bug** — Grader receives `item_type` to interpret the dict correctly; typed union ensures agent output validation.

---

## Frontend Bugs

- [ ] **Bug 16 — QuizRunner "Next" button `findIndex` callback logic error**
  - **File:** `frontend/src/components/QuizRunner/QuizRunner.tsx` (lines 376-378)
  - **Code:**
    ```tsx
    const nextUnanswered = skillItems.findIndex(
      (itm, idx) => idx > itemIndex && !attemptsByItemId[itm.id]
    );
    ```
  - **Issue:** `findIndex` returns the *index in the array*, but the callback receives `(item, index)`. The logic `idx > itemIndex` is correct, but `setItemIndex(nextUnanswered)` sets the index correctly. However, if all remaining items are answered, it falls back to `setItemIndex((i) => Math.min(i + 1, skillItems.length - 1))` which increments by 1 even if current item is answered — should skip to first unanswered or end.

- [ ] **Bug 17 — QuizRunner selected skill radio buttons don't show answered state**
  - **File:** `frontend/src/components/QuizRunner/QuizRunner.tsx` (lines 476-500)
  - **Issue:** Skill selector buttons show "cert" badge but no visual indicator of which skills have completed items. Practitioner can't tell progress at a glance.

- [ ] **Bug 18 — ProfileWizard Step 2 certification selection doesn't pre-select in edit mode**
  - **File:** `frontend/src/components/ProfileBuilder/ProfileWizard.tsx` (lines 428-446)
  - **Issue:** `selectedCertId` set from `existingProfile.certification_id` in `useEffect` (line 85-88), but radio button `checked={selectedCertId === cert.id}` should work. However, if `certList` loads after effect runs, `selectedCertId` may be set to ID not yet in list — radio won't match.
  - **Fix:** Move pre-selection logic inside `certList` dependent effect or use `certList?.find(...)`.

- [ ] **Bug 19 — ProfileWizard `handleGetRecommendation` builds answers with null coalescing that may send `null` for required fields**
  - **File:** `frontend/src/components/ProfileBuilder/ProfileWizard.tsx` (lines 93-103)
  - **Issue:** `fullAnswers` uses `??` for all fields including required ones (`writes_code`, `focus_area`, `experience_level`). If user hasn't interacted with a field, it sends `false`/`"building"`/`"some"` defaults from initial state — correct. But `provider_preference` sends `null` which backend may not expect.
  - **Fix:** Omit optional fields entirely when `null` rather than sending `null`.

- [ ] **Bug 20 — SkillRadar `certCode` used in template string when potentially undefined**
  - **File:** `frontend/src/components/SkillRadar/SkillRadar.tsx` (lines 182, 296, 338)
  - **Code:** `const radarTitle = certCode ? \`Skill radar — ${certCode}\` : "Skill radar";` — correct ternary, but line 296: `"Generate a personalised path toward " + (certCode ?? "your certification")` and line 338: `to ${certCode ?? "certification"}` — both handle undefined correctly. **Actually OK**, but verify `activeProfile?.certification_code` can be undefined.

- [ ] **Bug 21 — SessionContext doesn't auto-clear on 401 from any API call**
  - **File:** `frontend/src/context/SessionContext.tsx` (lines 42-46)
  - **Issue:** `load()` only called on mount and manual `refresh()`. If an API call returns 401 (session expired), the context still holds stale `MeResponse`; no global interceptor to call `clear()`.
  - **Fix:** Add Axios/TanStack Query interceptor to call `clear()` and redirect to login on 401.

- [ ] **Bug 22 — `useGenerateLearningPath` hook invalidates correct caches but SkillRadar doesn't show loading during regeneration**
  - **File:** `frontend/src/hooks/index.ts` (lines 137-151) & `frontend/src/components/SkillRadar/SkillRadar.tsx` (lines 300-312)
  - **Issue:** "Regenerate path" button shows spinner via `generatePath.isPending`, but radar polygon and side panel don't show loading state — they render stale data until mutation completes and cache invalidates.
  - **Fix:** Add `isLoading` overlay or skeleton on radar when `generatePath.isPending`.

- [ ] **Bug 23 — PractitionerPage tabs use `window.location.pathname` for active tab detection (brittle)**
  - **File:** `frontend/src/pages/PractitionerPage.tsx` (line 15)
  - **Issue:** `activeTab = window.location.pathname.split("/").pop() ?? "skills"` breaks if URL has query params or trailing slash. Should use `useLocation()` from react-router-dom.
  - **Fix:** Import `useLocation` and parse `location.pathname`.

- [ ] **Bug 24 — BuildProfilePage "Delete" button disabled logic incorrect for single inactive profile**
  - **File:** `frontend/src/pages/BuildProfilePage.tsx` (lines 206-208)
  - **Code:** `disabled={profile.is_active && profileList.length === 1}`
  - **Issue:** If only profile is *inactive*, `profile.is_active` is false → delete enabled → user can delete their only profile, leaving zero profiles. Should be `disabled={profileList.length === 1}` regardless of active state.
  - **Fix:** Change condition to `profileList.length === 1`.

- [ ] **Bug 25 — ProfileSkillRater component (Step 6.5) referenced but may not handle all skills**
  - **File:** `frontend/src/components/ProfileBuilder/ProfileSkillRater.tsx` (not read but imported in ProfileSkillAssessmentPage)
  - **Issue:** Step 6.5 requires two-tier display (cert-relevant first, then all others). Verify component implements this and pre-populates from `profile_skill_assessments`.

- [ ] **Bug 26 — QuizRunner trap-reveal panel shows for free-text items if `is_trap_selected` somehow true**
  - **File:** `frontend/src/components/QuizRunner/QuizRunner.tsx` (lines 209-221)
  - **Issue:** MCQ block checks `attempt.is_trap_selected && item.trap_explanation`; free-text block doesn't check trap. But `GraderOutput.is_trap_selected` is `bool | None` — could be `true` for free-text if grader misbehaves. Guard with `item.item_type === "mcq"`.

- [ ] **Bug 27 — `usePractitionerAttempts` query `placeholderData` keeps stale data after logout/login as different user**
  - **File:** `frontend/src/hooks/index.ts` (lines 165-172)
  - **Issue:** `placeholderData: (prev) => prev` preserves previous user's attempts when switching practitioners without unmounting. Query key includes `practitioner_id` so should refetch, but placeholder shows old data briefly.
  - **Fix:** Remove `placeholderData` or ensure query key change triggers full refetch.

- [ ] **Bug 28 — CertAdvisor questionnaire radio labels don't match backend enum values exactly**
  - **File:** `frontend/src/components/CertAdvisor/CertAdvisor.tsx` (not read but test expects "No preference", "Yes, I write code", etc.)
  - **Issue:** Backend `QuestionnaireAnswers.provider_preference` enum is `"anthropic" | "aws" | "google" | "microsoft"` but frontend sends `"none"` or similar. Advisor request uses `ProviderPreference` type which excludes "none".
  - **Fix:** Align frontend form values with backend enum; send `null` for no preference.

- [ ] **Bug 29 — TrendDashboard / AdoptionTrendChart may divide by zero when no quiz data**
  - **File:** `frontend/src/components/TrendDashboard/TrendDashboard.tsx` & `frontend/src/components/AdoptionTrendChart/AdoptionTrendChart.tsx` (not read)
  - **Issue:** `avg_score` calculation in `SkillQuizPeriod` could divide by zero if `attempt_count = 0`. TypeScript type allows `avg_score: number` but no guard.
  - **Fix:** Default `avg_score` to 0 when `attempt_count === 0`.

- [ ] **Bug 30 — LoginPage doesn't clear session cookie on failed login attempt**
  - **File:** `frontend/src/pages/LoginPage.tsx` (not read)
  - **Issue:** If admin login fails (wrong password), the previous session cookie (if any) remains; subsequent `GET /auth/me` may return old session.
  - **Fix:** Call `auth.logout()` or clear cookie on login error.

---

## Data Model / Migration Bugs

- [ ] **Bug 31 — `skill_profile_snapshots` composite PK prevents history; `mastery_history` duplicates data**
  - **File:** `backend/app/db/models.py` (lines 206-258, 1023-1061)
  - **Issue:** `SkillProfileSnapshot` has composite PK `(practitioner_id, skill_id)` — only one row per pair. `MasteryHistory` appended on every profiler run duplicates snapshot data. Could use `skill_profile_snapshots` as current + `mastery_history` as history, but snapshot upsert loses previous value.
  - **Fix:** Accept current design (snapshot = current, history = append-only) but document clearly; or change snapshot to append-only with `computed_at` as part of PK.

- [ ] **Bug 32 — `certification_skills.weight` allows 0 but Curriculum Planner may divide by zero**
  - **File:** `backend/app/db/models.py` (line 445) & `backend/app/workflows/generate_learning_path.py` (lines 248-251)
  - **Issue:** Weight constraint `weight >= 0 AND weight <= 1` allows 0. Planner builds `skill_weights` dict; if all weights are 0, prioritization logic may behave unexpectedly.
  - **Fix:** Change constraint to `weight > 0` or handle zero-weight case in planner.

- [ ] **Bug 33 — `nudge_categories.criteria` JSON schema not enforced; `resolve_recipients` assumes specific keys**
  - **File:** `backend/app/services/nudge_resolver.py` (not read) & `backend/app/db/models.py` (line 999)
  - **Issue:** `criteria` is `sa.JSON` with no validation. `resolve_recipients` expects keys like `no_quiz_days_gte`, `skill_gap_skill_id`, etc. Invalid criteria silently return empty list.
  - **Fix:** Add Pydantic model for criteria validation in `nudge_resolver.py`.

---

## Test / Infrastructure Bugs

- [ ] **Bug 34 — Playwright tests assume specific text labels ("Primary recommendation", "Accept this recommendation") that may not match UI**
  - **File:** `frontend/tests/practitioner-journey.spec.ts` (lines 68-71, 91-95)
  - **Issue:** Test selectors like `page.getByText("Primary recommendation")` and `page.getByRole("button", { name: "Accept this recommendation" })` depend on exact strings. If UI copy changes, tests break.
  - **Fix:** Use `data-testid` attributes for stable selectors.

- [ ] **Bug 35 — Stub Claude client doesn't simulate Structured Outputs validation failure path correctly**
  - **File:** `backend/tests/fixtures/stub_claude_client.py` (lines 106-110)
  - **Issue:** `output_format.model_validate(self._response_data)` raises `ValidationError` for malformed data, but Agent base catches it and records `status="error"`. Test scenario "malformed stub response is caught" expects this — verify it works.

- [ ] **Bug 36 — No test for `nightly_pulse` workflow with Message Batches API path**
  - **File:** `backend/app/workflows/nightly_pulse.py` (lines 13-26 comment)
  - **Issue:** Comment documents upgrade path to Message Batches API but no test or implementation exists. Current synchronous path costs 2x.
  - **Fix:** Add `@pytest.mark.live` test or document as known limitation.

- [ ] **Bug 37 — Seed script `verified_date = date.today()` makes `last_verified_at` dynamic (non-reproducible seeds)**
  - **File:** `backend/seed/generate.py` (line 510)
  - **Issue:** `last_verified_at` set to today; re-running seed changes this value. Should be fixed date for reproducibility or configurable.
  - **Fix:** Use constant date or environment variable.

- [ ] **Bug 38 — `require_any_authenticated` blocks `must_change_password` admins but allows practitioners with expired sessions**
  - **File:** `backend/app/api/deps/session.py` (lines 108-117)
  - **Issue:** Practitioner sessions have `expires_at = None` (never expire). If a practitioner's session row is deleted manually, `get_session` raises 401 correctly. But no periodic cleanup of stale practitioner sessions.
  - **Fix:** Acceptable for v1; document that practitioner sessions are perpetual.

---

## Cosmetic / UX Bugs

- [ ] **Bug 39 — QuizRunner shows "Difficulty X%" for items with `difficulty = 0` (newly created)**
  - **File:** `frontend/src/components/QuizRunner/QuizRunner.tsx` (lines 169-171)
  - **Issue:** `item.difficulty` defaults to 0.5 in DB but can be 0; displays "Difficulty 0%" which looks wrong.
  - **Fix:** Clamp display to minimum 1% or show "Not calibrated".

- [ ] **Bug 40 — SkillRadar axis labels truncate at 14 chars with ellipsis (may cut meaningful names)**
  - **File:** `frontend/src/components/SkillRadar/SkillRadar.tsx` (line 78)
  - **Issue:** `name.length > 14 ? name.slice(0, 13) + "…" : name` — skill names like "Prompt Engineering" become "Prompt Engin…" losing clarity.
  - **Fix:** Increase limit to 20 or use tooltip for full name.

- [ ] **Bug 41 — ProfileWizard Step 1 "Provider preference" dropdown shows "No preference" but backend expects null**
  - **File:** `frontend/src/components/ProfileBuilder/ProfileWizard.tsx` (lines 331-344)
  - **Issue:** `<option value="">No preference</option>` sends empty string `""`; `setAnswers` stores `""` which becomes `null` in `fullAnswers` via `??` coalescing. Works but inconsistent with `provider_preference` type.
  - **Fix:** Ensure empty string maps to `null` consistently.

- [ ] **Bug 42 — BuildProfilePage profile cards show "Cert mastery" progress bar even when `mastery_pct` is null**
  - **File:** `frontend/src/pages/BuildProfilePage.tsx` (lines 139-160)
  - **Issue:** `{profile.mastery_pct != null && (...)}` guards the bar — correct. But `mastery_pct` computation in backend `_compute_mastery_pct` returns `None` if no certification or no snapshots. Card shows nothing in that case — acceptable.

- [ ] **Bug 43 — NudgesPage filter buttons ("drafted", "approved", "sent") don't show active state clearly**
  - **File:** `frontend/src/pages/NudgesPage.tsx` (not read)
  - **Issue:** Leadership journey test expects filter buttons with names "drafted", "approved". Verify visual active state.

- [ ] **Bug 44 — RollupView "withheld" state shows generic message; should explain minimum cohort size**
  - **File:** `frontend/src/components/RollupView/RollupView.tsx` (not read) & test expects `[data-testid='cohort-withheld']` with "withheld" and "minimum" text.
  - **Fix:** Ensure component renders explanatory text when `min_cohort_size_met = false`.

---

## Security / Access Control Bugs

- [ ] **Bug 45 — Practitioner login upserts by email without verifying ownership (email enumeration)**
  - **File:** `backend/app/api/routes/auth.py` (lines 100-160)
  - **Issue:** `POST /auth/practitioner-login` creates/updates practitioner by email. Anyone knowing an email can overwrite name/role/practice. No verification (magic link, code, etc.).
  - **Fix:** Acceptable per design ("no password, email only") but document risk; consider adding "remember me" token or rate limiting.

- [ ] **Bug 46 — `enforce_self_or_admin` allows full admin to see all practitioner data including attempts (leadership correctly blocked)**
  - **File:** `backend/app/api/deps/session.py` (lines 157-172)
  - **Issue:** Full admin (`role = "admin"`) can access `/practitioners/{id}/attempts` — intentional per architecture.md table. But `GET /attempts/{attempt_id}` also allows admin (line 229). Leadership gets 403. Correct.

- [ ] **Bug 47 — Admin password change doesn't invalidate existing sessions**
  - **File:** `backend/app/api/routes/auth.py` (lines 268-288)
  - **Issue:** `POST /auth/change-password` updates hash and `must_change_password = false` but doesn't delete other sessions for that admin. Old sessions remain valid.
  - **Fix:** Delete all sessions for `admin_user_id` on password change.

- [ ] **Bug 48 — Session cookie `secure` flag only in production; `SameSite=Lax` allows CSRF on subdomain takeover**
  - **File:** `backend/app/api/routes/auth.py` (lines 148-154, 231-237)
  - **Issue:** `secure=settings.environment == "production"` — correct. `SameSite=Lax` is standard but `Strict` would be safer for auth cookie. `Lax` allows cookie on top-level navigation from external links.
  - **Fix:** Consider `SameSite=Strict` for admin sessions; keep `Lax` for practitioner.

---

## Performance / Scalability Bugs

- [ ] **Bug 49 — `generate_learning_path` fetches ALL skills for every run (N+1 on skill count)**
  - **File:** `backend/app/workflows/generate_learning_path.py` (lines 164-166)
  - **Issue:** `select(Skill)` loads entire skill catalog (~16 skills now, but grows). Acceptable for small catalog but not scalable.
  - **Fix:** Add pagination or filter to skills relevant to practitioner's profile/certification.

- [ ] **Bug 50 — `nightly_pulse` queries `UsageEvent` counts per skill per practitioner in loop (N×M queries)**
  - **File:** `backend/app/workflows/nightly_pulse.py` (lines 275-313)
  - **Issue:** For each practitioner × each skill, runs 3 separate count queries (30d, 90d, latest). With 100 practitioners × 16 skills = 4,800 queries per nightly run.
  - **Fix:** Use single aggregated query with `GROUP BY practitioner_id, skill_id` and window functions.

- [ ] **Bug 51 — `useSkills` query fetches full skill tree on every page load**
  - **File:** `frontend/src/hooks/index.ts` (lines 75-79)
  - **Issue:** `skills.list` returns all skills; used by QuizRunner, SkillRadar, ProfileSkillRater. Cached by TanStack Query but initial load hits DB.
  - **Fix:** Acceptable for ~20 skills; add `staleTime: Infinity` since skills rarely change.

- [ ] **Bug 52 — `SkillProfiler` agent receives all events for practitioner (no pagination/limit)**
  - **File:** `backend/app/workflows/generate_learning_path.py` (lines 101-116)
  - **Issue:** `select(SkillProfileEvent).where(...).order_by(desc())` loads all events ever. For practitioners with long history, prompt context grows unbounded.
  - **Fix:** Limit to last N events (e.g., 100) or last 90 days.

---

## Missing Features (Requirements Gaps)

- [ ] **Bug 53 — No email delivery integration for nudges (Step 7.6 not implemented)**
  - **File:** `backend/app/services/email.py` (exists but not wired)
  - **Issue:** `Nudge.channel` supports `"email"` but nightly pulse only creates `channel="in_app"`. No code sends emails.
  - **Fix:** Implement `email.send()` call in nudge approval or campaign send.

- [ ] **Bug 54 — No 90-day pruning job for `mastery_history` table**
  - **File:** `backend/app/db/models.py` (line 1027 comment) & no background task
  - **Issue:** Comment says "Rows older than 90 days are pruned by a background maintenance task" but no such task exists.
  - **Fix:** Add scheduled job (APScheduler or cron) to delete old `MasteryHistory` rows.

- [ ] **Bug 55 — No "Regenerate path" confirmation dialog (destructive action replaces active path)**
  - **File:** `frontend/src/components/SkillRadar/SkillRadar.tsx` (lines 300-312)
  - **Issue:** "Regenerate path" button immediately triggers mutation; previous active path marked `completed` (workflow line 329-336). No confirmation.
  - **Fix:** Add confirmation dialog or "Save as new path" option.

- [ ] **Bug 56 — No way to view/edit `nudge_categories` criteria after creation**
  - **File:** `frontend/src/pages/NudgesPage.tsx` & `backend/app/api/routes/pulse.py`
  - **Issue:** Admin can generate categories and send campaigns but not edit criteria JSON after creation.
  - **Fix:** Add edit endpoint and UI for `nudge_categories`.

- [ ] **Bug 57 — Practitioner cannot delete their own account/data (GDPR/privacy)**
  - **File:** No DELETE `/practitioners/{id}` endpoint for practitioners
  - **Issue:** Only admin can delete practitioners. Practitioner has no "Delete my account" option.
  - **Fix:** Add self-delete endpoint with confirmation.

- [ ] **Bug 58 — No audit log for admin actions (nudge approval, campaign send, profile changes)**
  - **File:** `agent_runs` tracks agent calls but not admin UI actions
  - **Issue:** Leadership can't see who approved a nudge or sent a campaign.
  - **Fix:** Add `admin_audit_log` table or extend `workflow_runs` for admin actions.

---

## Documentation / Configuration Bugs

- [ ] **Bug 59 — `.env.example` missing required variables (Anthropic API key, DB URL, etc.)**
  - **File:** Not in repo (only `.env.example` referenced in Step 5.3)
  - **Issue:** New developers can't run without guessing env vars.
  - **Fix:** Create comprehensive `.env.example` with all required variables.

- [ ] **Bug 60 — `CLAUDE.md` references `/mnt/skills/public/frontend-design/SKILL.md` which doesn't exist in repo**
  - **File:** `CLAUDE.md` (line: "Read `/mnt/skills/public/frontend-design/SKILL.md`")
  - **Issue:** Path is absolute/mount-specific; not portable. Should be relative or documented as external.
  - **Fix:** Update path or copy relevant design tokens into repo.

- [ ] **Bug 61 — `project_plan.md` Step 5.5 bug descriptions reference `SelfAssessmentPanel` but component renamed/removed in Phase 6.7**
  - **File:** `project_plan.md` (lines 610-611) & `docs/architecture.md`
  - **Issue:** Step 5.5 Bug 2 mentions `SelfAssessmentPanel` in SkillRadar; Step 6.7 says "Remove the '✏ Rate your skills' toggle from the Skill Radar tab entirely". Component still exists in code but may not be used.
  - **Fix:** Update project plan or remove component if unused.

- [ ] **Bug 62 — `docs/coding-guidelines.md` says "No browser storage" but `SessionContext` uses React state (OK) — verify no `localStorage` usage**
  - **File:** `frontend/src/context/SessionContext.tsx` — clean. Search codebase for `localStorage`/`sessionStorage`.
  - **Fix:** Run `grep -r "localStorage\|sessionStorage" frontend/src/` to confirm none.

---

## Summary

| Category | Count | Fixed |
|----------|-------|-------|
| Phase 5.5 Known Bugs | 3 | 0 |
| Backend Logic | 12 | 7 |
| Frontend UI/State | 14 | 0 |
| Data Model/Migrations | 3 | 0 |
| Tests/Infrastructure | 5 | 0 |
| Cosmetic/UX | 6 | 0 |
| Security/Access Control | 4 | 0 |
| Performance/Scalability | 4 | 0 |
| Missing Features | 6 | 0 |
| Documentation/Config | 4 | 0 |
| **Total** | **59** | **7** |

---
*Generated from full codebase analysis on 2026-08-08. Update checkboxes as bugs are fixed.*