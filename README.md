# Mastery Pulse

A two-sided AI training platform: **Mastery Mesh** (certification advisor,
skill profiling, personalized learning paths with a trap-reveal quiz mechanic)
and **Adoption Pulse** (usage signals, trained-vs-adopted gap analysis, nudges,
leadership rollups). The two halves share a skill graph and close a feedback loop.

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

> **Note:** the migration downgrade test (`test_downgrade_reverses_cleanly`) leaves
> `mastery_pulse` empty. Run `py -m alembic upgrade head` again afterward to restore it.

## Environment

Copy `.env.example` to `.env` and fill in your `ANTHROPIC_API_KEY`. All other
values have sensible defaults for local development.

## Auth

Two login paths on the same landing page (`/login`):

| Role | How to log in | Default credentials |
|---|---|---|
| **Practitioner** | Name + email (no password) | Any name + email — upserted on entry |
| **Admin / Leadership** | Check "I'm an admin" toggle → email + password | `admin@example.com` / `welcome` (must change on first login) |

Practitioners land directly on their own dashboard. Admins get the full practitioners list and admin nav (Rollups, Nudges, Admin Users, Observability).

### Admin user management

Full admins can add and remove admin/leadership accounts from **Admin Users** in the nav bar
(`/admin-users`). Each new user is assigned a temporary password and must change it on first login.
Leadership accounts see rollups and nudges but cannot access individual practitioner data or manage other admin users.

| API endpoint | Who can call |
|---|---|
| `GET /api/v1/admin-users` | Admin only |
| `POST /api/v1/admin-users` | Admin only |
| `DELETE /api/v1/admin-users/{id}` | Admin only (cannot delete self) |

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
| `project_plan.md` | Step-by-step build plan with DoD gates |
| `docs/architecture.md` | Nine agents, orchestration, MCP strategy, model selection, auth design |
| `docs/data-model.md` | Postgres schema and certification seed catalog |
| `docs/coding-guidelines.md` | Python/TS conventions, testing philosophy |
| `docs/human-in-the-loop.md` | The ten 👤 steps that need Ayan's judgment |
| `docs/demo-script.md` | Step-by-step demo for the two core journeys |
