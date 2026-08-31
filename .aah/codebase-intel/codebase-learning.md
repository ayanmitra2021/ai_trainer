# Codebase Learning Document

**Project**: Mastery Pulse (ai_trainer)
**Profiled**: 2026-08-31
**Primary Language**: Python 3.11+
**Codebase Size**: 232 source files, 54,474 lines (148 Python, 42 TSX, 26 TypeScript, + config/docker/SQL/shell)

---

## 1. System Purpose and Context
Mastery Pulse is an AI-powered learning and adoption platform for Deloitte practitioners. It has two integrated loops:
- **Mastery Mesh**: Recommends the right certification (Anthropic, AWS, Google Cloud, Microsoft, etc.), profiles the practitioner's current skills, builds a personalized learning path, and generates/grades practice items (MCQs, free-text, scenarios) with a trap-reveal mechanic for common misconceptions.
- **Adoption Pulse**: Watches real-world usage signals (Claude Code activity, git commits via local MCP servers) and calculates whether the mastery actually shows up in day-to-day work. Gaps feed individual nudges (coached messages) that require human approval before delivery.

The two halves close a feedback loop: Adoption Pulse findings prioritize what Curriculum Planner targets next.

---

## 2. Technology Stack
| Category | Technology | Version (if known) | Notes |
|----------|------------|-------------------|-------|
| Language | Python | 3.11+ | Backend, agents, MCP servers |
| Language | TypeScript | ^5.5.3 | Frontend |
| Framework | FastAPI | >=0.115 | REST API + async ASGI |
| ORM | SQLAlchemy async | >=2.0 | All DB access |
| Migrations | Alembic | >=1.13 | 22 revisions |
| Database | PostgreSQL + pgvector | — | Primary store |
| AI | Anthropic Claude Haiku 4.5 | claude-haiku-4-5-20251001 | Structured outputs |
| AI | NVIDIA Nemotron Ultra 253B + Lightning 70B | — | OpenAI-compatible endpoint |
| Frontend | React 18 + Vite | ^18.3.1 / ^5.4.2 | SPA |
| 3D | Three.js + @react-three/fiber | ^0.168.0 | Portal3D component |
| State | TanStack Query v5 | ^5.56.2 | Server state caching |
| Protocol | MCP (stdio) | >=1.0 | Local data adapters |

---

## 3. Architecture Overview
The system follows a **layered monolith** pattern on the backend — not microservices. All eleven agents are in-process Python classes that inherit from a shared `Agent` ABC. Workflows orchestrate agents by calling them sequentially; no event bus, no background task queue in the core path.

- **Architectural style**: Layered monolith (API → Workflow → Agent → Model Client → LLM Provider → DB)
- **Layer structure**: API routes (FastAPI) → Workflow orchestrators → Agent layer (11+ LLM-backed) → MultiTierModelClient → Anthropic / NVIDIA → SQLAlchemy → PostgreSQL
- **Key design patterns**:
  - **Typed Structured Outputs**: Agents never parse JSON from raw text; they use `client.messages.parse()` with a Pydantic output model
  - **Prompt-file pattern**: Every agent's system prompt lives in `agents/prompts/<agent_name>.md`, loaded at runtime
  - **Append-only event tables**: `skill_profile_events`, `usage_events`, `correlation_snapshots` are never updated — Agents append; readers derive state
  - **Provider chain with circuit breaker**: NVIDIA Ultra → Lightning → Haiku with in-memory NvidiaCircuitBreaker
  - **Human-in-the-loop gates**: Nudge delivery (drafted → approved → sent), domain proposal review (pending_review → approved/rejected)

---

## 4. Codebase Structure
| Directory | Purpose | Key Files |
|-----------|---------|-----------|
| `backend/app/` | Core application | `main.py`, `config.py` |
| `backend/app/db/` | Data layer | `models.py` (2083 lines, 40+ ORM classes), `session.py`, `migrations/` |
| `backend/app/api/routes/` | HTTP endpoints | 16 route modules, one per domain |
| `backend/app/api/deps/` | FastAPI dependencies | `session.py` (auth guards), `plan.py` |
| `backend/app/agents/` | LLM agent implementations | `base.py`, `model_client.py`, 14+ agent files, `prompts/` |
| `backend/app/workflows/` | Agent orchestrators | One workflow per user journey |
| `backend/app/mcp_servers/` | Local MCP adapters | `learning_portal/`, `usage_signals/` |
| `backend/app/schemas/` | Pydantic API schemas | One file per domain |
| `backend/tests/scenarios/` | Given/When/Then tests | `test_phase*.py` files |
| `frontend/src/` | React SPA | `api/`, `hooks/`, `components/`, `pages/` |
| `docs/` | Architecture and design docs | Parsed into knowledge base |

---

## 5. Data Architecture
- **Primary store**: PostgreSQL with asyncpg for runtime, psycopg2 for Alembic migrations
- **Schema evolution**: 22 Alembic revisions aligned to development phases
- **Key patterns**:
  - Composite PKs on snapshot tables (`skill_profile_snapshots`: `practitioner_id + skill_id`)
  - Append-only tables for audit and history (`skill_profile_events`, `usage_events`, `mastery_history`, `correlation_snapshots`)
  - Soft-delete via `deleted_at` on `practitioner_profiles` (Phase 22)
  - Version-frozen foreign keys: `practitioner_profiles.domain_version_id` is locked at profile-lock time and never retroactively shifted
  - `CHECK` constraints everywhere (status enums, score ranges 0–1)
  - Cross-database compatibility: `sa.JSON` in models (Postgres uses JSONB in DDL); SQLite in unit tests without a constraint like partial indexes
- **Data flow**: All LLM agent outputs write to the DB through the caller (routes / workflows) — agents themselves don't persist; callers do

---

## 6. API Surface
| Endpoint/Interface | Method | Purpose |
|-------------------|--------|---------|
| `/api/v1/auth/practitioner-login` | POST | Upsert practitioner by email, set session cookie |
| `/api/v1/auth/admin-login` | POST | Verify admin password, set session cookie |
| `/api/v1/auth/me` | GET | Return current session identity |
| `/api/v1/auth/enrollment-info` | GET | Public — org enrollment code metadata |
| `/api/v1/practitioners` | GET/POST/PATCH | Practitioner CRUD + deactivation |
| `/api/v1/profiles` | GET/POST/PATCH/DELETE | Profile management + skill assessments |
| `/api/v1/certifications` | GET | Certification catalog |
| `/api/v1/learning-paths` | GET/POST | LP generation + item retrieval |
| `/api/v1/pulse` | GET | Correlation snapshots, trend data |
| `/api/v1/nudges` | GET/POST/PATCH | Nudge inbox, approval workflow |
| `/api/v1/mock-exams` | GET/POST/PATCH | Exam session lifecycle |
| `/api/v1/cert-discovery` | POST | Trigger CertDomainDiscovery agent |
| `/api/v1/observability` | GET | Agent run / workflow run monitoring |
| `/api/v1/product-admin` | GET/POST/PATCH | Product-admin org/plan management |
| `/api/v1/notification-settings` | GET/PATCH | Org notification preferences |
| MCP stdio (learning_portal) | — | Local data adapter for learning content |
| MCP stdio (usage_signals) | — | Local adapter for Claude Code / git signals |

---

## 7. Key Abstractions
| Concept | Implementation | Files |
|---------|---------------|-------|
| Agent | Abstract base class with typed IO, structured outputs, agent_runs audit row | `agents/base.py` |
| ModelClient | Protocol + MultiTierModelClient (3-tier chain with circuit breaker) | `agents/model_client.py` |
| Session (auth) | Opaque UUID cookie, server-side Session ORM row, `identity_type` discriminator | `db/models.py`, `api/deps/session.py` |
| PractitionerProfile | Locked snapshot of cert goal + skill assessments; domain_version frozen at lock time | `db/models.py`, `api/routes/profiles.py` |
| CertificationDomainVersion | Versioned exam domain snapshot; enables live domain refresh without retroactive changes | `db/models.py`, `agents/cert_domain_discovery.py` |
| Nudge | Human-gated coach message (drafted → approved → sent); never auto-delivered | `db/models.py`, `api/routes/nudges.py` |
| CorrelationSnapshot | Append-only gap history; trained_score vs adoption_score per practitioner × skill | `db/models.py`, `agents/correlation.py` |
| Organization / SubscriptionPlan | Multi-tenant containers with tier-aware feature gates (Phase 22) | `db/models.py`, `api/routes/product_admin.py` |

---

## 8. Dependency Analysis
- **High-impact modules** (change carefully):
  - `app.db.models` — 84 dependents; a column rename or type change ripples across the entire codebase
  - `app.agents.model_client` — 34 dependents (all agents via `base.py`); changing the `parse()` signature or error types affects every LLM call
  - `app.agents.base` — 14 agents inherit it; changing the `run()` loop or `agent_runs` schema affects agent telemetry everywhere
- **Well-isolated modules** (safe to modify independently):
  - Individual route modules (`api/routes/auth.py`, etc.) — only `main.py` imports them
  - Individual agent files — only their workflow imports them
  - Individual schema files — only their route imports them
- **No circular dependencies** detected; the no-agent-imports-agent rule is structurally clean

---

## 9. Testing Landscape
- **Framework**: pytest + pytest-asyncio (async test mode = `auto`, session scope loop)
- **Test style**: Scenario tests (Given/When/Then) in `backend/tests/scenarios/`; no mocks — all tests run against real business logic
- **Test isolation**: SQLite (via aiosqlite) for unit/scenario tests; `pg_engine` fixture drops and recreates tables for integration tests (marked `@pytest.mark.integration`)
- **Test markers**:
  - `integration` — requires live Postgres (skipped by default)
  - `live` — calls real Anthropic API (never on CI)
  - `mcp_roundtrip` — spawns a real MCP subprocess
- **Coverage gaps**: No frontend unit tests (Playwright E2E only); mock_exam, byte_sized_lesson, product_admin routes have limited scenario coverage

---

## 10. Build and Deployment
- **Backend build**: Docker (`backend/Dockerfile`); uvicorn as ASGI server
- **Frontend build**: Vite (`npm run build`), outputs `dist/`; `postbuild` copies `index.html` to `404.html` for GitHub Pages SPA routing
- **CI/CD**: GitHub Actions (`.github/` workflows)
- **Frontend hosting**: GitHub Pages via `gh-pages`
- **Env config**: `.env.example` (committed, safe placeholders) + `.env` (gitignored, real secrets); pydantic-settings reads all config at startup
- **DB migrations**: `alembic upgrade head` must run after writing any migration

---

## 11. Technical Debt and Risks
| Area | Observation | Impact | Confidence |
|------|-------------|--------|------------|
| `app.db.models` size | Single 2083-line file defining 40+ ORM classes | Hard to navigate; any migration requires reading the whole file | High |
| SQLite partial index gap | `CertificationDomainVersion` partial unique index (WHERE is_current=true) is silently dropped on SQLite | Unit tests don't enforce the "one current version per cert" constraint | High |
| `create_haiku_only_client()` is banned | CLAUDE.md / memory says NEVER use this; use `create_model_client()` | Using it bypasses the provider chain, making NVIDIA credits unused | High |
| No pgvector wiring | pgvector is in the schema but no agent uses it yet | Dead provisioned infrastructure | Medium |
| Practitioner sessions never expire | `expires_at` is null for practitioners (admin sessions do expire) | Long-lived sessions; security consideration for enterprise deployments | Medium |
| Frontend no localStorage policy | CLAUDE.md bans localStorage/sessionStorage | Requires all state via TanStack Query + cookies; easy to accidentally violate | Medium |
| Rollup model archived | `RollupReporter` in `agents/_deprecated/rollup_reporter.py`; rollups table dropped | Dead code present; shouldn't cause issues but adds cognitive noise | Low |

---

## 12. Recommendations for Modification
- **Where to start**: Read `main.py` (router wiring) → `db/models.py` (schema) → `agents/base.py` (agent contract) → a specific agent (e.g. `certification_advisor.py`) to understand the typed-IO + structured-output pattern
- **What to be careful about**:
  - Any change to `db/models.py` requires an Alembic migration (`alembic upgrade head` immediately after writing the migration)
  - Any new agent must follow the Agent ABC contract (no direct agent-to-agent imports, prompt in `prompts/<name>.md`, typed input/output)
  - Always use `create_model_client()` — NEVER `create_haiku_only_client()` directly (per memory/CLAUDE.md)
  - No browser storage (localStorage/sessionStorage) anywhere in the frontend
  - Nudge delivery is always human-gated — don't add auto-send logic
- **What to test after changes**: Run `py -m pytest` from `backend/` for scenario tests. For migration changes, run `alembic upgrade head` against a clean schema
- **Potential pitfalls**:
  - The NVIDIA → Haiku fallback chain means a test calling an agent may silently switch providers; check `agent_run.model_used` in observability
  - Phase 22 added multi-tenancy — routes that query `practitioners` or `admin_users` should now filter by `organization_id` where relevant
  - `domain_version_id` on profiles is frozen at lock time — never update it post-lock; new cert domain refreshes create a new version row, not update the existing one
