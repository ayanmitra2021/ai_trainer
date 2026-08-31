# Dependency Map

## External Dependencies

### Backend (pyproject.toml)

| Package | Version | Purpose | Category |
|---------|---------|---------|----------|
| fastapi | >=0.115 | REST API framework | Web |
| uvicorn[standard] | >=0.30 | ASGI server | Web |
| sqlalchemy[asyncio] | >=2.0 | ORM + async engine | Database |
| alembic | >=1.13 | Schema migrations | Database |
| asyncpg | >=0.29 | Async Postgres driver (app) | Database |
| psycopg2-binary | >=2.9 | Sync Postgres driver (alembic only) | Database |
| pydantic | >=2.9 | Data validation + Structured Outputs | Validation |
| pydantic-settings | >=2.5 | Environment config Settings | Config |
| python-dotenv | >=1.0 | .env file loading | Config |
| anthropic[mcp] | >=0.40 | Anthropic Claude API + MCP client | AI |
| mcp | >=1.0 | MCP protocol library | AI |
| openai | >=1.40 | NVIDIA NIM API (OpenAI-compatible) | AI |
| bcrypt | >=4.0 | Password hashing | Auth |
| python-multipart | >=0.0.9 | Form data parsing | Web |
| faker | >=26.0 | Test/seed data generation | Dev Utility |
| pytest | >=8.3 | Test framework | Dev |
| pytest-asyncio | >=0.24 | Async test support | Dev |
| httpx | >=0.27 | Async HTTP client for tests | Dev |
| ruff | >=0.6 | Linter + formatter | Dev |
| black | >=24.0 | Code formatter | Dev |
| aiosqlite | >=0.20 | SQLite async driver for unit tests | Dev |

### Frontend (package.json)

| Package | Version | Purpose | Category |
|---------|---------|---------|----------|
| react | ^18.3.1 | UI framework | Frontend |
| react-dom | ^18.3.1 | DOM rendering | Frontend |
| react-router-dom | ^6.26.2 | Client-side routing | Frontend |
| @tanstack/react-query | ^5.56.2 | Server state management + caching | Frontend |
| three | ^0.168.0 | 3D rendering (Portal3D component) | Frontend |
| @react-three/fiber | ^8.17.10 | React wrapper for Three.js | Frontend |
| @react-three/drei | ^9.122.0 | Three.js helpers / abstractions | Frontend |
| typescript | ^5.5.3 | Type checking | Dev |
| vite | ^5.4.2 | Build tool + dev server | Dev |
| @vitejs/plugin-react | ^4.3.1 | Vite React fast-refresh plugin | Dev |
| @playwright/test | ^1.47.2 | End-to-end testing | Dev |
| eslint | ^9.9.1 | Linting | Dev |
| gh-pages | ^6.3.0 | GitHub Pages deployment | Dev |

## Internal Module Dependencies

| Module | Depends On | Depended By |
|--------|-----------|-------------|
| `app.db.models` | sqlalchemy, uuid, datetime | 84 modules (all routes, all agents) |
| `app.agents.model_client` | anthropic, openai, app.config | all agents (via base) |
| `app.agents.base` | model_client, db.models, pydantic | all agent implementations |
| `app.config` | pydantic-settings, python-dotenv | model_client, all routes |
| `app.db.session` | sqlalchemy asyncio, app.config | all routes (via Depends) |
| `app.api.deps.session` | db.models, db.session, config | all route modules |
| `app.api.routes.*` | deps.session, db.models, db.session, schemas | app.main |
| Individual agents | base, db.models | workflow modules, routes |
| `app.workflows.*` | multiple agents, db.session | routes |
| `frontend/src/hooks/index.ts` | @tanstack/react-query, api/index | all page components |
| `frontend/src/api/types.ts` | (none — type definitions) | hooks, components, pages |
