# Mastery Pulse — Demo Script

Step-by-step script for the two core journeys. Run against a fresh local stack
(local Postgres + seeded data). Takes roughly 15 minutes end-to-end.

## Prerequisites

```bash
# 1. Start the backend
cd backend
alembic upgrade head
py -m seed.generate
uvicorn app.main:app --reload

# 2. Start the frontend (separate terminal)
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

Starter admin credentials: `admin@example.com` / `welcome` (must change on first login).

---

## Journey 1 — Practitioner: from unknown to learning path

### 1.1 Log in as a practitioner

1. Open `http://localhost:5173` — the login page appears.
2. Enter:
   - **Name:** Alex Rivera
   - **Email:** alex.rivera@mastery.example
   - **Org level:** Senior Consultant
3. Click **Continue**.
   - Expected: redirected directly to Alex's dashboard (Skill Radar, Certifications, Quiz, Trends tabs).

### 1.2 Get a certification recommendation

1. Click the **Certifications** tab.
2. Click **Get a recommendation**.
3. Answer the questionnaire:
   - Provider preference: **Anthropic**
   - Writes code: **No**
   - Focus area: **Advising / business use**
   - Experience: **Some exposure**
4. Submit.
   - Expected: recommendation = **CCAO-F** (Claude Certified Associate – Foundations) with rationale.
5. Click **Accept recommendation** to move the goal to `selected`.

### 1.3 Generate a personalized learning path

1. Click the **Skill Radar** tab.
2. Click **Regenerate learning path**.
   - Expected: spinner while Skill Profiler → Curriculum Planner → Item-Writer runs.
   - Expected: radar updates; path items appear.

### 1.4 Attempt a quiz item

1. Click the **Quiz** tab.
2. Select any skill and start a question.
3. Deliberately select the **trap option** (the plausible-but-wrong answer).
   - Expected: the trap-reveal panel slides in explaining the misconception.
4. Submit a second attempt, selecting the correct option.
   - Expected: correct-answer state shown; score 1.0.

### 1.5 Verify radar reflects the attempt

1. Return to **Skill Radar**.
2. Click **Regenerate learning path** again.
   - Expected: the profiled skill's mastery score has moved based on the quiz result.

---

## Journey 2 — Leadership: rollup view and nudge approval

### 2.1 Log in as admin

1. Click **Log out** (top-right) to end the practitioner session.
2. Check **"I'm an admin / leadership member"**.
3. Enter `admin@example.com` / `welcome`.
4. On the password-change screen, set a new password (at least 8 characters).
   - Expected: redirected to the admin home (practitioners list).

### 2.2 Add a leadership user

1. Click **Admin Users** in the nav bar.
2. Click **+ Add user**.
3. Fill in:
   - **First name:** Sam
   - **Email:** sam.leader@mastery.example
   - **Role:** Leadership — aggregates only
   - **Temporary password:** Welcome123
4. Click **Create user**.
   - Expected: the new row appears in the table with status "Pending password change".
5. Optionally click **Remove** on any user to delete them (you cannot remove your own account).

### 2.4 Trigger the nightly pulse

Use the API directly (or Swagger at `http://localhost:8000/docs`):

```bash
# Get a practitioner ID first
curl http://localhost:8000/api/v1/practitioners   \
  -H "Cookie: mastery_session=<your_admin_cookie>"

# Trigger the pulse
curl -X POST http://localhost:8000/api/v1/pulse/run \
  -H "Content-Type: application/json" \
  -H "Cookie: mastery_session=<your_admin_cookie>" \
  -d '{
    "practitioner_ids": ["<alex_id>"],
    "scope": "team",
    "scope_ref": "AI&E",
    "period_start": "2026-07-01T00:00:00",
    "period_end": "2026-08-06T23:59:59"
  }'
```

Expected: `{ "status": "completed", "rollup_id": "..." }`.

### 2.5 Approve a nudge

1. In the frontend, click **Nudges** in the nav.
2. Find a nudge in `drafted` status.
3. Click **Approve** — status moves to `approved`.
   - Expected: status badge changes; timestamp set.

### 2.6 View a rollup

1. Click **Rollups** in the nav.
2. Find the rollup created for `AI&E`.
   - Expected: shows aggregate metrics (avg gap score, % with adoption gaps).
   - If `min_cohort_size_met = false`: a "data withheld" banner appears instead of numbers.

### 2.7 Observability check

1. Click **Observability** in the nav (admin-only — hidden for leadership).
2. Verify:
   - Total runs reflect the pulse + learning path workflow runs.
   - Any errors from those runs appear in **Recent errors** with their messages.

---

## Confirming privacy gates

| Test | Expected |
|---|---|
| Log in as leadership admin → click Nudges | 200 — nudges visible |
| Log in as leadership admin → call `GET /attempts/{id}` | 403 — blocked |
| Log in as practitioner → call `GET /practitioners/{other_id}/skill-profile` | 403 — blocked |
| Admin with `must_change_password=true` → call any data endpoint | 403 — blocked |

---

## Full regression smoke-check

```bash
# From backend/
cd backend
py -m pytest                                         # unit + scenario tests
py -m pytest -m integration                          # requires local Postgres
py -m pytest tests/scenarios/test_auth.py -v        # auth scenarios
py -m pytest tests/scenarios/test_observability.py -v  # observability scenario

# From frontend/
cd frontend
npx playwright test                                  # E2E journeys
```

Expected: zero failures across all suites.
