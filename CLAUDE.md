# CLAUDE.md — Mastery Pulse

## What this is

One app built from two ideas that share a skill graph. **Mastery Mesh** starts by helping a practitioner pick the right certification for their background and goals — Anthropic, AWS, Google Cloud, Microsoft, or anything else in the catalog, not Anthropic-only — then profiles their skills, builds a personalized learning path targeting it, and writes/grades practice items (with a trap-reveal mechanic for common misconceptions). **Adoption Pulse** watches real usage signals (Claude Code activity, commit patterns) to see whether that mastery shows up in actual work, and turns the gap into individual nudges. The two halves close a loop — Adoption Pulse's findings feed back into what the Curriculum Planner prioritizes next.

**Certification-domain alignment (Phase 10 design constraint):** a profile cannot exist without a certification associated. Quiz items are tagged against the cert's official exam domains; the domain gap bar chart shows readiness by exam domain, driven only by cert-evaluated quiz answers. The broad Skill Radar (10–15 overarching skills) is updated by all quiz answers. Self-assessment at profile creation time gives an initial domain-score estimate; ongoing score changes come only from quiz performance.

"Mastery Pulse" is a working title. Rename freely — it's a find-and-replace, not a decision.

Built mostly via Claude Code, with a few parts (marked 👤 in `project_plan.md`) written directly by Ayan — usually a prompt, a rubric, or a policy call, not plumbing.

## Tech stack

Python 3.11+ / FastAPI / SQLAlchemy / Alembic · Postgres (+ `pgvector`) · React + TypeScript (Vite) · ten LLM-API-backed agents orchestrated by plain async Python (no LangGraph/Temporal) · custom local MCP servers for internal data sources · **dual-model support: Anthropic Claude (default) or NVIDIA Nemotron 3 Ultra via `APP_BRAIN_MODEL` env var**.

## Repo map

```
mastery-pulse/
├── CLAUDE.md              (this file)
├── project_plan.md        (the build plan — work through it one step at a time)
├── docs/                   architecture.md · data-model.md · coding-guidelines.md · human-in-the-loop.md
├── backend/app/            agents/ · mcp_servers/ · workflows/ · api/routes/ · db/
├── backend/tests/scenarios/
└── frontend/src/           pages/ · components/ · api/
```
Full tree: `docs/architecture.md`.

## Building this project

Work through `project_plan.md` one step at a time, in order — each step only assumes what the *previous* step's Definition of Done already guarantees. Run `/clear` between steps; that's expected and safe. Don't skip ahead even if a later step looks easy.

## Non-negotiable conventions

- **Agents share one contract** (`backend/app/agents/base.py`): typed input, typed output via Structured Outputs, one `agent_runs` row per call. Never hand-parse JSON from a text response. Full contract in `docs/architecture.md`.
- **Prompts are files, not strings.** Each agent's system prompt lives at `agents/prompts/<agent_name>.md`, loaded at runtime — never inline in Python.
- **MCP servers run locally (stdio)** via the `anthropic[mcp]` client-side pattern, not Anthropic's hosted MCP connector — the connector needs a public HTTPS endpoint, which these adapters don't have. Don't reach for `mcp_servers`/`mcp_toolset` API params without re-reading the note in `docs/architecture.md` first.
- **Tests are scenarios, not units.** Given/When/Then, run against a stub Claude client. A step is only done when its scenario tests are green — say so plainly if they're not, rather than reporting a step complete. Full approach in `docs/coding-guidelines.md`.
- **No agent imports another agent.** Cross-agent data flow is the workflow's job.
- **No browser storage** (`localStorage`/`sessionStorage`) anywhere in the frontend.

## Where Ayan is in the loop

Ten steps across the plan need a human judgment call — a prompt's pedagogy, a grading rubric, a privacy threshold, a UI beat — not just code. They're flagged 👤 inline in `project_plan.md`; full rationale in `docs/human-in-the-loop.md`. If a task looks like it's drifting into one of those without having been flagged, stop and ask rather than guessing.

## Reference docs (read on demand, not all at once)

- `docs/architecture.md` — the nine agents, orchestration, MCP strategy, model selection.
- `docs/data-model.md` — the Postgres schema, including the certification catalog.
- `docs/coding-guidelines.md` — conventions, prompt-file pattern, testing approach in full.
- `docs/human-in-the-loop.md` — the ten 👤 steps, with reasoning.
- `docs/MULTI_PROVIDER.md` — migration guide for dual-provider support (Phase 8).

`project_plan.md` names which of these to open for each step — no need to load them all every session.

## Maintaining this file

Keep it under ~180 lines. If something needs adding, ask whether it belongs here or in `docs/` before appending. Run `/doctor` occasionally to catch drift. Personal-only preferences (editor, verbosity, local ports) go in `CLAUDE.local.md`, which is gitignored — not here.
