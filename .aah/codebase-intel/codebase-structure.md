# Codebase Structure

## Directory Layout

```
ai_trainer/                          # project root
├── CLAUDE.md                        # project instructions + AAH delivery block
├── project_plan.md                  # build plan (phases 0–22)
├── README.md
├── .env.example                     # env var names with safe placeholders (committed)
├── .env                             # real secrets (gitignored)
├── .aah/                            # AAH framework state
│   └── codebase-intel/              # this directory
├── docs/                            # reference docs + knowledge base
│   ├── architecture.md
│   ├── data-model.md
│   ├── coding-guidelines.md
│   ├── human-in-the-loop.md
│   ├── multi_provider_architecture.md
│   └── demo-script.md
├── scripts/                         # utility scripts
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml               # Python project config + ruff/black/pytest settings
│   └── app/
│       ├── main.py                  # FastAPI application entrypoint
│       ├── config.py                # pydantic-settings Settings class
│       ├── db/
│       │   ├── models.py            # ALL SQLAlchemy ORM models (2083 lines)
│       │   ├── session.py           # async engine + get_db dependency
│       │   └── migrations/          # Alembic migration scripts (22 phases)
│       ├── api/
│       │   ├── deps/
│       │   │   ├── session.py       # session cookie auth guards (get_session, require_admin)
│       │   │   └── plan.py          # learning plan dependencies
│       │   └── routes/
│       │       ├── auth.py          # login, logout, me, enrollment-info
│       │       ├── practitioners.py # CRUD + deactivation
│       │       ├── skills.py        # skill graph endpoints
│       │       ├── certifications.py
│       │       ├── learning_paths.py
│       │       ├── profiles.py      # practitioner profiles + skill assessments
│       │       ├── pulse.py         # adoption pulse / correlation data
│       │       ├── nudges.py        # nudge inbox + approval
│       │       ├── mock_exams.py    # exam session management
│       │       ├── cert_domain_versions.py
│       │       ├── cert_discovery.py
│       │       ├── byte_sized_lessons.py
│       │       ├── product_admin.py # product-admin tier routes
│       │       ├── notification_settings.py
│       │       ├── admin_users.py   # org-admin CRUD
│       │       └── observability.py # agent_runs / workflow_runs dashboard
│       ├── agents/
│       │   ├── base.py              # Agent ABC — typed IO, structured outputs, agent_runs
│       │   ├── model_client.py      # MultiTierModelClient, NvidiaCircuitBreaker, factory
│       │   ├── certification_advisor.py
│       │   ├── curriculum_planner.py
│       │   ├── item_writer.py
│       │   ├── quiz_batch_generator.py
│       │   ├── grader.py
│       │   ├── domain_scorer.py
│       │   ├── skill_profiler.py
│       │   ├── usage_signal.py
│       │   ├── correlation.py
│       │   ├── nudge_composer.py
│       │   ├── nudge_category_generator.py
│       │   ├── nudge_campaign_composer.py
│       │   ├── cert_domain_discovery.py
│       │   ├── cert_skill_mapper.py
│       │   ├── mock_exam_generator.py
│       │   ├── byte_sized_lesson.py
│       │   ├── round_metrics.py
│       │   └── prompts/             # system prompt .md files (one per agent)
│       ├── mcp_servers/
│       │   ├── learning_portal/server.py    # stdio MCP for learning content
│       │   └── usage_signals/server.py      # stdio MCP for Claude Code + git signals
│       ├── schemas/                 # Pydantic request/response schemas
│       │   ├── certifications.py
│       │   ├── practitioners.py
│       │   ├── profiles.py
│       │   ├── learning_paths.py
│       │   ├── items.py
│       │   ├── skills.py
│       │   ├── pulse.py
│       │   ├── nudge_campaign.py
│       │   └── cert_domain_versions.py
│       └── workflows/               # workflow orchestrators (no LangGraph)
└── frontend/
    ├── Dockerfile
    ├── package.json                 # React 18 + Three.js + TanStack Query
    ├── vite.config.ts
    └── src/
        ├── api/
        │   ├── index.ts             # axios/fetch client setup
        │   └── types.ts             # shared TS types (86 symbols — hotspot)
        ├── hooks/
        │   └── index.ts             # TanStack Query hooks (91 symbols — hotspot)
        ├── components/
        │   ├── Portal3D/            # Three.js 3D portal scene
        │   ├── PortalLayout/        # top-level layout + nav
        │   ├── CertAdvisor/         # cert recommendation UI
        │   ├── CertDomainGapChart/  # domain readiness bar chart
        │   ├── AdoptionTrendChart/  # mastery-vs-adoption trend chart
        │   └── NudgeInbox/          # in-app nudge notifications
        └── pages/                   # React Router page components
```

## Entry Points

| File | Role | Description |
|------|------|-------------|
| `backend/app/main.py` | Backend entrypoint | FastAPI app init, CORS, exception handlers, all 16 router includes |
| `backend/app/mcp_servers/learning_portal/server.py` | MCP server | Stdio MCP server for learning portal data |
| `backend/app/mcp_servers/usage_signals/server.py` | MCP server | Stdio MCP server for usage signal ingestion |
| `frontend/src/api/index.ts` | Frontend API client | Base HTTP client for all API calls |

## API Routes

| Prefix | Router Module | Phase | Description |
|--------|--------------|-------|-------------|
| `/api/v1/practitioners` | practitioners | 2 | Practitioner CRUD, deactivation |
| `/api/v1/skills` | skills | 2 | Skill graph read |
| `/api/v1/certifications` | certifications | 2 | Cert catalog |
| `/api/v1/learning-paths` | learning_paths | 2 | LP management + item retrieval |
| `/api/v1/pulse` | pulse | 3 | Adoption pulse / correlation snapshots |
| `/api/v1/auth` | auth | 5 | Login (practitioner + admin), logout, me, enrollment-info |
| `/api/v1/observability` | observability | 5 | agent_runs / workflow_runs monitoring |
| `/api/v1/admin-users` | admin_users | 5 | Admin user CRUD |
| `/api/v1/profiles` | profiles | 6 | Practitioner profile management |
| `/api/v1/nudges` | nudges | 7 | Nudge inbox, approval, campaigns |
| `/api/v1/cert-domain-versions` | cert_domain_versions | 10.2 | Domain version history |
| `/api/v1/mock-exams` | mock_exams | 11 | Exam session lifecycle |
| `/api/v1/cert-discovery` | cert_discovery | 13 | Cert Domain Discovery agent trigger |
| `/api/v1/byte-sized-lessons` | byte_sized_lessons | 18 | Micro-lesson generation |
| `/api/v1/product-admin` | product_admin | 22 | Product-admin tier management |
| `/api/v1/notification-settings` | notification_settings | 22 | Org notification preferences |

## Module Organization
The backend is organized by **architectural layer** (db, api, agents, mcp_servers, workflows, schemas). Within `agents/`, each file is one agent; `prompts/` holds their system prompt Markdown files loaded at runtime. The frontend is organized by **component type** (pages, components, hooks, api). The dual-layer structure (Mastery Mesh + Adoption Pulse) is reflected in the data models and agent names rather than in separate directories.
