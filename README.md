# Mastery Pulse

A two-sided AI training platform: **Mastery Mesh** (certification advisor,
skill profiling, personalized learning paths, trap-reveal quiz mechanic, mock
exams, byte-sized lessons) and **Adoption Pulse** (usage signals,
trained-vs-adopted gap analysis, smart nudges). The two halves share a skill
graph and close a feedback loop. Multi-tenant SaaS with subscription plans,
organization enrollment codes, and a product admin portal.

## Prerequisites

- **PostgreSQL 14+** installed and running locally on port 5432
- Create two databases (once, as a superuser):
  ```sql
  CREATE USER mastery WITH PASSWORD 'mastery';
  CREATE DATABASE mastery_pulse OWNER mastery;
  CREATE DATABASE mastery_pulse_test OWNER mastery;
  ```
- **Python 3.11+** (invoke as `py` on Windows)
- **Node.js 18+**

## Quick start

```bash
# 1. Install backend deps
cd backend
py -m pip install -e ".[dev]"

# 2. Run migrations
py -m alembic upgrade head

# 3. Seed the database
py -m seed.generate

# 4. Start the API
uvicorn app.main:app --reload

# 5. Install & run the frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Running tests

```bash
cd backend

# Unit tests (no Postgres required — uses in-memory SQLite)
py -m pytest -m "not integration" -v

# Integration tests (requires mastery_pulse_test database)
py -m pytest -m integration -v

# Everything at once
py -m pytest -v
```

```bash
# End-to-end tests (Playwright — requires the app to be running)
cd frontend
npx playwright test
```

> **Note:** the migration downgrade test (`test_downgrade_reverses_cleanly`) leaves
> `mastery_pulse` empty. Run `py -m alembic upgrade head` again afterward to restore it.

## Environment

Copy `.env.example` to `.env`. The table below lists every variable; required
ones must be set before the app starts (the startup env-checker fails with
`ERR_CDR_78_EX_CONFIG` and names any missing variable).

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | ✅ | Async Postgres connection (`postgresql+asyncpg://…`) |
| `ANTHROPIC_API_KEY` | ✅ | Anthropic API key (used when `APP_BRAIN_MODEL=ANTHROPIC`) |
| `APP_BRAIN_MODEL` | ✅ | `NVIDIA` (production) or `ANTHROPIC` (local dev) |
| `NVIDIA_API_KEY` | NVIDIA mode | NVIDIA NIM API key |
| `NVIDIA_MODEL_ID_PRIMARY` | NVIDIA mode | Tier-1 model (Nemotron Ultra) |
| `NVIDIA_MODEL_ID_SECONDARY` | NVIDIA mode | Tier-2 model (Nemotron Lightning) |
| `NVIDIA_BASE_URL` | NVIDIA mode | NIM API base URL |
| `APP_ANTHROPIC_MODEL_ID` | — | Locked to `claude-haiku-4-5-20251001`; change only intentionally |
| `ALLOWED_ORIGINS` | — | CORS origins (e.g. GitHub Pages URL → Render) |
| `NVIDIA_TIER1_TIMEOUT_SECS` | — | Default `10` |
| `NVIDIA_TIER2_TIMEOUT_SECS` | — | Default `20` |
| `ANTHROPIC_TIER_TIMEOUT_SECS` | — | Default `20` |
| `NVIDIA_CIRCUIT_BREAKER_THRESHOLD` | — | Failures before open (default `5`) |
| `NVIDIA_CIRCUIT_BREAKER_COOLDOWN_SECS` | — | Cooldown period (default `120`) |

## Auth

### Practitioner & admin logins

Two login paths on the same landing page (`/login`):

| Role | How to log in | Default credentials |
|---|---|---|
| **Practitioner** | Name + email (no password) | Any name + email — upserted on entry |
| **Admin / Leadership** | Check "I'm an admin" toggle → email + password | `admin@example.com` / `welcome` (must change on first login) |

Practitioners land directly on their own dashboard. Admins get the full
practitioners list and admin nav (Nudges, Admin Users, Observability).

Leadership accounts see nudges but cannot access individual practitioner data or manage other admin users.

### Admin user management

Full admins can add and remove admin/leadership accounts from **Admin Users** in
the nav bar (`/admin-users`). Each new user is assigned a temporary password and
must change it on first login.

| API endpoint | Who can call |
|---|---|
| `GET /api/v1/admin-users` | Admin only |
| `POST /api/v1/admin-users` | Admin only |
| `DELETE /api/v1/admin-users/{id}` | Admin only (cannot delete self) |

### Product admin portal

A separate login at `/product-admin` for SaaS operators (not org admins).
Product admins manage subscription plans, create organizations, generate
enrollment codes, and change their own password.

| API endpoint | Who can call |
|---|---|
| `POST /api/v1/product-admin/login` | Product admin |
| `GET /api/v1/product-admin/plans` | Product admin |
| `POST /api/v1/product-admin/organizations` | Product admin |
| `POST /api/v1/product-admin/enrollment-codes` | Product admin |

## Features

### Mastery Mesh

- **Certification Advisor** — recommends a target certification (Anthropic, AWS,
  Google Cloud, Microsoft, and others) based on role and goals; also adapts to
  results from an organization's learning-portal MCP.
- **Practitioner Profile & Skill Assessment** — a guided wizard captures the
  target certification, a self-assessed skill baseline, and a per-domain
  readiness estimate. Profiles can be locked once complete.
- **Certification Domain Alignment** — quiz items are tagged against official
  exam domains. Domain gap bar chart shows readiness per domain. Exam domain
  definitions are versioned and admin-refreshable via the Cert Domain Discovery
  Agent — no code change needed when an exam is revised.
- **Personalized Learning Path** — Curriculum Planner builds a path ordered by
  domain gap. Displayed as a road-map with the Skill Radar (10–15 overarching
  skills) and a 3D skill-calibration view.
- **Quiz Runner (trap-reveal mechanic)** — practice items with per-answer
  rationales reveal common misconceptions on wrong answers. Background
  generation keeps a per-skill queue so there is always a next question.
- **Mock Exams** — timed, full-length sessions assembled by the Mock Exam
  Generator agent. Smart question recycling avoids repeating items seen in prior
  sessions. Session history table and per-session confidence score gauge.
- **Byte-Sized Lessons** — short AI-generated lessons surfaced alongside quiz
  items. Read-aloud via the Web Speech API TTS hook.

### Adoption Pulse

- **Usage Signals** — Claude Code session data and commit patterns ingested via
  the local `usage-signals` MCP server.
- **Trained-vs-Adopted Gap Analysis** — Correlation agent compares quiz mastery
  scores against actual usage patterns.
- **Smart Nudge System** — Nudge Category Generator and Campaign Composer agents
  produce targeted nudges routed to individual inboxes. Supports email delivery
  and Teams webhook notifications (enterprise).
- **Trend Dashboard** — charts for adoption trend, progress over time, and
  session activity.

### Admin & Observability

- **Admin Practitioner Activity View** — shows activity summary per practitioner
  with a Deactivate button for inactive accounts.
- **Observability page** — `agent_runs` log accessible to admins for debugging
  agent call latency and errors.
- **Interactive User Guide** — `/guide` page with role-gated sections and an
  "Ask Ayan" chat widget.

## Multi-provider AI (three-tier chain)

All agents route through `MultiTierModelClient` (see `docs/multi_provider_architecture.md`):

```
NVIDIA Nemotron Ultra (10 s) → NVIDIA Nemotron Lightning (20 s) → Anthropic Haiku (20 s) → 503 degraded
```

- Set `APP_BRAIN_MODEL=NVIDIA` to use the free-tier NVIDIA chain (production default).
- Set `APP_BRAIN_MODEL=ANTHROPIC` to use Anthropic Haiku directly (local dev).
- An in-memory circuit breaker opens after 5 consecutive failures per provider
  and holds for 120 s before re-probing.
- When all providers are unavailable the API returns a graceful 503 with a
  `ProviderUnavailable` toast in the UI rather than crashing.

## MCP Servers

Two local MCP servers run via stdio (not the hosted Anthropic connector):

| Server | Entry point | Tools exposed |
|---|---|---|
| `mcp-learning-portal` | `backend/app/mcp_servers/learning_portal/server.py` | `get_certifications`, `get_course_completions`, `get_self_assessment` |
| `mcp-usage-signals` | `backend/app/mcp_servers/usage_signals/server.py` | `get_claude_code_sessions`, `get_commit_activity` |

Both are registered as CLI entry points in `pyproject.toml` and invoked by
agents using the `anthropic[mcp]` client-side pattern.

## Deployment

Production infrastructure:

| Layer | Service |
|---|---|
| Database | Supabase (Postgres 15, direct port-5432 asyncpg connection) |
| Backend API | Render (deploy-hook triggered by CI) |
| Frontend | GitHub Pages (SPA fallback: `dist/404.html` copied from `index.html`) |

### CI/CD

`.github/workflows/deploy.yml` runs on push to `master` (or manual
`workflow_dispatch`). Steps: install deps → run migrations against Supabase →
trigger Render deploy hook → `npx gh-pages -d dist`.

Required GitHub Actions secrets: `DATABASE_URL_MIGRATE`, `RENDER_DEPLOY_HOOK_URL`.

### Manual deploy

```bash
# Requires scripts/.env.deploy (see scripts/.env.deploy.example)
bash scripts/deploy.sh

# Skip individual steps
bash scripts/deploy.sh --skip-migrate
bash scripts/deploy.sh --skip-backend
bash scripts/deploy.sh --skip-frontend
```

## Docker

```bash
# Backend
docker build -t mastery-pulse-backend ./backend
docker run -p 8000:8000 --env-file .env mastery-pulse-backend

# Frontend
docker build -t mastery-pulse-frontend ./frontend
docker run -p 80:80 mastery-pulse-frontend
```

Both containers expect Postgres as an external managed service (not included in the images).

## Docs

| File | What it covers |
|---|---|
| `CLAUDE.md` | Codebase conventions, repo map, non-negotiables |
| `project_plan.md` | Step-by-step build plan (22 phases) with DoD gates |
| `docs/architecture.md` | Twelve agents, orchestration, MCP strategy, model selection, auth design |
| `docs/data-model.md` | Postgres schema and certification seed catalog |
| `docs/coding-guidelines.md` | Python/TS conventions, testing philosophy |
| `docs/human-in-the-loop.md` | The ten 👤 steps that need Ayan's judgment |
| `docs/demo-script.md` | Step-by-step demo for the two core journeys |
| `docs/multi_provider_architecture.md` | Three-tier provider chain, circuit breaker, APP_BRAIN_MODEL |
