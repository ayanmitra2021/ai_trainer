# Mastery Pulse

A two-sided AI training platform: **Mastery Mesh** (certification advisor,
skill profiling, personalized learning paths with a trap-reveal quiz mechanic)
and **Adoption Pulse** (usage signals, trained-vs-adopted gap analysis, nudges,
leadership rollups). The two halves share a skill graph and close a feedback loop.

## Quick start

> Read `CLAUDE.md` for the full project context and conventions.  
> Read `project_plan.md` for the step-by-step build plan.

```bash
# 1. Start Postgres
docker compose up -d

# 2. Install backend deps (Python 3.11+)
cd backend
py -m pip install -e ".[dev]"

# 3. Run migrations
alembic upgrade head

# 4. Seed the database
py -m seed.generate

# 5. Start the API
uvicorn app.main:app --reload

# 6. Install & run the frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Running tests

```bash
cd backend

# Unit tests (no Postgres required — uses in-memory SQLite)
py -m pytest -m "not integration"

# Integration tests (requires docker compose up -d)
py -m pytest -m integration
```

## Docs

| File | What it covers |
|---|---|
| `CLAUDE.md` | Codebase conventions, repo map, non-negotiables |
| `project_plan.md` | Step-by-step build plan with DoD gates |
| `docs/architecture.md` | Nine agents, orchestration, MCP strategy, model selection |
| `docs/data-model.md` | Postgres schema and certification seed catalog |
| `docs/coding-guidelines.md` | Python/TS conventions, testing philosophy |
| `docs/human-in-the-loop.md` | The ten 👤 steps that need Ayan's judgment |
