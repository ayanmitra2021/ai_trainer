# Technology Stack

| Category | Technology | Version | Purpose |
|----------|------------|---------|---------|
| **Language** | Python | 3.11+ | Backend, agents, MCP servers |
| **Language** | TypeScript | ^5.5.3 | Frontend type-safe React |
| **Language** | SQL | — | Database migrations (Alembic DDL) |
| **Framework** | FastAPI | >=0.115 | REST API, async request handling, CORS |
| **Framework** | React | ^18.3.1 | SPA frontend |
| **ORM** | SQLAlchemy | >=2.0 | Async ORM, Declarative Base, relationship mapping |
| **Migrations** | Alembic | >=1.13 | PostgreSQL schema migrations (22 revisions) |
| **Database** | PostgreSQL | — | Primary relational data store |
| **DB Extension** | pgvector | — | Vector embeddings (provisioned) |
| **DB Driver** | asyncpg | >=0.29 | Async Postgres driver for runtime |
| **DB Driver** | aiosqlite | >=0.20 | SQLite async driver for unit tests |
| **Validation** | Pydantic v2 | >=2.9 | Request/response schemas, Structured Output models |
| **Config** | pydantic-settings | >=2.5 | Env-var backed Settings class |
| **AI SDK** | anthropic[mcp] | >=0.40 | Claude Haiku 4.5 structured outputs + MCP client |
| **AI SDK** | openai | >=1.40 | NVIDIA NIM (Nemotron Ultra/Lightning) — OpenAI-compatible |
| **AI Model** | Claude Haiku 4.5 | claude-haiku-4-5-20251001 | Default Anthropic model (Tier 3 fallback in NVIDIA mode) |
| **AI Model** | Nemotron Ultra 253B | nvidia/llama-3.1-nemotron-ultra-253b-v1 | Primary model in NVIDIA mode (Tier 1) |
| **AI Model** | Nemotron Lightning 70B | nvidia/llama-3.1-nemotron-70b-instruct | NVIDIA Tier 2 fallback |
| **Protocol** | MCP (Model Context Protocol) | >=1.0 | Local stdio MCP servers for data adapters |
| **Auth** | bcrypt | >=4.0 | Password hashing for admin + product-admin |
| **ASGI** | uvicorn[standard] | >=0.30 | Production ASGI server |
| **Build** | Vite | ^5.4.2 | Frontend build tool + HMR dev server |
| **3D** | Three.js | ^0.168.0 | 3D portal component |
| **3D** | @react-three/fiber | ^8.17.10 | React renderer for Three.js |
| **3D** | @react-three/drei | ^9.122.0 | Three.js abstractions (orbit controls, etc.) |
| **Data Fetching** | TanStack Query | ^5.56.2 | Server state, caching, background refetch |
| **Routing** | React Router | ^6.26.2 | Client-side routing |
| **Linting** | ruff | >=0.6 | Python linting + import sorting |
| **Formatting** | black | >=24.0 | Python code formatting |
| **Testing** | pytest + pytest-asyncio | >=8.3 / >=0.24 | Backend scenario tests (Given/When/Then) |
| **Testing** | httpx | >=0.27 | Async HTTP client for test scenarios |
| **Testing** | Playwright | ^1.47.2 | Frontend E2E tests |
| **Infrastructure** | Docker | — | Container packaging (backend + frontend Dockerfiles) |
| **CI** | GitHub Actions | — | CI/CD workflows |
| **Deployment** | GitHub Pages | — | Frontend static hosting (gh-pages) |
