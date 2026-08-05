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

## Docs

| File | What it covers |
|---|---|
| `CLAUDE.md` | Codebase conventions, repo map, non-negotiables |
| `project_plan.md` | Step-by-step build plan with DoD gates |
| `docs/architecture.md` | Nine agents, orchestration, MCP strategy, model selection |
| `docs/data-model.md` | Postgres schema and certification seed catalog |
| `docs/coding-guidelines.md` | Python/TS conventions, testing philosophy |
| `docs/human-in-the-loop.md` | The ten 👤 steps that need Ayan's judgment |
