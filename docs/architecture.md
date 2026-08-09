# Architecture — Mastery Pulse

Reference doc. Read this before building any agent, workflow, or MCP server. Pairs with `docs/data-model.md` (what's stored) and `docs/coding-guidelines.md` (how it's coded).

## The product in one paragraph

Mastery Pulse is one app built from two ideas that share a skill graph. **Mastery Mesh** is the front stage: it starts by helping a practitioner pick the right certification for their background and goals — Anthropic, AWS, Google Cloud, Microsoft, or whatever else is in the catalog — then profiles their skills, builds a personalized learning path targeting it, and writes and grades practice items (with a trap-reveal mechanic for common misconceptions). **Adoption Pulse** is the back stage: it watches real usage signals (Claude Code activity, commit patterns) to see whether mastery earned in the front stage shows up in actual work, surfaces the gap, and turns it into individual nudges and leadership rollups. The two halves close a loop: Adoption Pulse's gaps feed back into what the Curriculum Planner prioritizes next.

Nothing about the design is Anthropic-specific. The certification catalog (`docs/data-model.md`) is provider-agnostic by construction, and the Certification Advisor agent reasons over whatever's in that catalog rather than having any one provider's exams baked into its prompt.

## Agent inventory

Each agent is a single-purpose, typed unit: one input contract, one output contract (a Pydantic model, enforced via Structured Outputs — see below), one row in `agent_runs` per call. An agent never decides on its own to call another agent; a **workflow** (plain Python, not a framework) sequences them. This keeps every agent independently testable and keeps the control flow visible in code instead of hidden inside a graph the human has to reconstruct mentally.

| # | Agent | Job | Reads | Writes |
|---|---|---|---|---|
| 1 | Certification Advisor | Match a short questionnaire to a best-fit certification | `certifications`, `certification_providers`, `certification_skills` | `certification_advisor_responses`, `practitioner_certification_goals` (status `recommended`) |
| 2 | Skill Profiler | Turn raw signals into a current mastery estimate | `skill_profile_events`, MCP: `mcp-learning-portal` | `skill_profile_snapshots`, `mastery_history` |
| 3 | Curriculum Planner | Pick what a practitioner should work on next | `skill_profile_snapshots`, `correlation_snapshots`, `practitioner_certification_goals` (if set) | `learning_paths`, `learning_path_items` |
| 4 | Item-Writer | Generate/calibrate practice items, incl. trap-reveal | `items`, `attempts` (calibration stats) | `items` |
| 5 | Grader | Score an attempt, incl. free-text, with rationale | `items`, submitted response | `attempts` |
| 6 | Usage-Signal | Ingest real usage evidence, map it to skill nodes | MCP: `mcp-usage-signals` | `usage_events` |
| 7 | Correlation | Compare "trained" vs. "adopting" per skill | `skill_profile_snapshots`, `usage_events` | `correlation_snapshots` |
| 8 | Nudge Composer | Draft an individual tone-checked nudge (nightly pulse) or a campaign message (admin-initiated) | `correlation_snapshots`, `nudge_categories` | `nudges` (status: `drafted` or `sent`) |
| 9 | Rollup Reporter | Aggregate, privacy-safe leadership narrative | `correlation_snapshots` (aggregated) | `rollups` |
| 10 | Nudge Category Generator | Analyze aggregate KPI data and propose up to 10 nudge categories with machine-readable criteria | `practitioners`, `skill_profile_snapshots`, `attempts`, `usage_events`, `nudges` (aggregate counts only — no PII) | `nudge_categories` (via API) |

Four workflows compose them:
- **`recommend_certification`**: Certification Advisor alone (Phase 2) — the actual front door for a new practitioner.
- **`generate_learning_path`**: Skill Profiler → Curriculum Planner → Item-Writer (Phase 2) — reads the practitioner's active certification goal if `recommend_certification` has already run, but doesn't require it.
- **`nightly_pulse`**: Usage-Signal → Correlation → Nudge Composer → Rollup Reporter (Phase 3)
- **`nudge_campaign`**: Nudge Category Generator → Nudge Composer (Phase 7) — admin-initiated; runs on demand, not on a schedule.

## Certification Advisor: the entry point

The questionnaire is short on purpose — a handful of targeted questions, not a long intake form:

1. Which certification body are you most interested in — Anthropic, AWS, Google Cloud, Microsoft, or no preference?
2. Do you write code as part of your role, or plan to?
3. Is your day-to-day focus closer to advising/business use, building applications, or designing/architecting systems?
4. How much hands-on experience do you already have in this area — new to it, some exposure, or experienced?

The agent's job is to match these answers against the current catalog and return a primary recommendation plus a short rationale (and, where relevant, one alternative with the trade-off named — e.g. "Architect Foundations has no hard prerequisite, but Developer Foundations is a gentler ramp if you're newer to building"). The catalog is passed to the agent as structured context on every call, not baked into the prompt as static knowledge — this is what lets a newly-added provider or a newly-retired exam take effect immediately instead of waiting for a prompt rewrite. See `docs/data-model.md` for the current seed catalog and why it's dated (`last_verified_at`) rather than assumed permanent.

The actual weighting — what to recommend when the answers don't cleanly point to one certification — is flagged 👤 in `docs/human-in-the-loop.md`.

## Agent contract

Every agent implements the same shape (built once, in Step 0.4, then reused nine times):

```python
class Agent(Generic[TInput, TOutput]):
    name: str
    model: str
    output_model: type[TOutput]          # Pydantic model — the Structured Output schema

    async def run(self, input: TInput) -> TOutput:
        ...  # builds prompt, calls Claude, persists an agent_runs row, returns typed output
```

Agents that need external data reach it via MCP tools (below), not by importing another agent's code or hitting the database directly for facts outside their own tables — that boundary is what keeps nine agents from turning into a tangle.

## Structured output, not string parsing

Every agent call uses Structured Outputs (`output_config.format` with a JSON Schema, or the Python SDK's `client.messages.parse(output_format=MyPydanticModel, ...)` convenience) rather than asking Claude to "respond in JSON" and hoping. This is a current, non-beta Claude API feature — no beta header required — and it removes an entire category of "the agent returned malformed JSON" bugs before they happen. Strict tool use (`strict: true` on tool schemas) does the equivalent for any tool the agent calls. The two compose: an agent can call MCP tools *and* return a structured final answer in the same request.

One caveat worth designing around from day one: property order in the response follows schema order with required fields first, and enum casing isn't perfectly guaranteed — compare enum values case-insensitively rather than with `==`.

## MCP strategy: local now, hosted later

Two custom MCP servers, because nothing pre-built covers internal exports:

- **`mcp-learning-portal`** — tools: `get_certifications`, `get_course_completions`, `get_self_assessment`, wrapping whatever Learning Portal / Power BI exports land in a local folder.
- **`mcp-usage-signals`** — tools: `get_claude_code_sessions`, `get_commit_activity`, wrapping local session logs and git history.

**This matters:** Claude's hosted MCP connector (the `mcp_servers` / `mcp_toolset` parameters on the Messages API) requires the server to be reachable over public HTTPS — Anthropic's cloud calls out to it. A local stdio server on your laptop is not reachable that way, and that's exactly what these two adapters are for v1. So the MVP pattern is the **client-side** one: the backend itself is the MCP client. Concretely, each agent that needs one of these tools uses the `anthropic[mcp]` extra (`pip install "anthropic[mcp]"`, needs Python 3.10+) together with the official `mcp` package's `stdio_client` / `ClientSession`, converts the MCP tools with `async_mcp_tool(...)`, and hands them to `client.beta.messages.tool_runner(...)` so Claude decides when to call them within its own turn:

```python
from anthropic.lib.tools.mcp import async_mcp_tool
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

server_params = StdioServerParameters(command="mcp-learning-portal")
async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as mcp_client:
        await mcp_client.initialize()
        tools = await mcp_client.list_tools()
        runner = client.beta.messages.tool_runner(
            model=MODEL,
            messages=[...],
            tools=[async_mcp_tool(t, mcp_client) for t in tools.tools],
        )
        result = await runner.until_done()
```

This is still genuinely "multi-agent orchestration with MCP servers and tool calls" — the orchestrator decides *which* MCP server an agent gets wired to, and Claude decides *which tools* to call within that — it's just Claude calling tools directly rather than routing through Anthropic's hosted connector.

**Upgrade path (not MVP):** if these adapters ever move behind a real HTTPS endpoint — e.g. this graduates from a personal tool to something hosted for the wider practice — switch to the hosted MCP connector: define servers in `mcp_servers` (`type: "url"`, `url`, `name`), configure tool visibility per-server via `mcp_toolset` in `tools` (current beta header: `mcp-client-2025-11-20` — the older `mcp-client-2025-04-04` shape with inline `tool_configuration` is deprecated). Worth revisiting once there's a real reason to, not before.

**Considered and deliberately not used for v1:** Anthropic's Managed Agents + Memory Stores (the sandboxed-agent-session platform you used for the Institutional Memory Agent hackathon build). It's a good fit for open-ended, bash/file-tool-driven agent exploration — it's the wrong fit here, where every agent's job is "fetch structured data, reason, return one typed answer." Forcing that into sandboxed agent sessions adds session/event-stream complexity and public-beta risk for no real benefit. The one place it could genuinely earn its keep later: giving the Item-Writer or Curriculum Planner a qualitative, cross-practitioner "notes to self" memory (e.g. which phrasings tend to confuse people) that doesn't fit as structured rows — a Phase 6+ idea, not a v1 dependency.

## Orchestration: hand-rolled, on purpose

No LangGraph/Temporal for v1. A `workflows/` module with plain async functions that call agents in sequence, writing a `workflow_runs` row at start and a status at the end. For a solo-maintained system, "read the Python function top to bottom" beats "reconstruct what a graph framework is doing" every time you need to debug a 2am nightly-job failure. Revisit only if a workflow needs branching complex enough that a hand-rolled sequence becomes the harder-to-read option — none of the three current workflows are there.

## Model selection

Default to **Claude Sonnet 5** (`claude-sonnet-5`) unless a row below says otherwise. Verify against [the current models overview](https://platform.claude.com/docs/en/about-claude/models/overview) before you build each agent — new models ship often enough that this table is a starting point, not gospel, by the time you reach Phase 3.

| Agent | Default (Anthropic) | NVIDIA | Why |
|---|---|---|---|
| Certification Advisor | Sonnet 5 | Nemotron 3 Ultra | Matching + explaining against structured catalog context — moderate reasoning, not the highest stakes |
| Skill Profiler | Sonnet 5 | Nemotron 3 Ultra | Structured extraction across a few signal sources — moderate reasoning |
| Curriculum Planner | Sonnet 5 | Nemotron 3 Ultra | Sequencing/planning, moderate complexity |
| Item-Writer | Sonnet 5 (escalate to **Opus 5** for the hardest trap items) | Nemotron 3 Ultra | Pedagogical judgment; most items don't need the top tier |
| Grader | **Opus 5** for free-text/rubric grading; **Haiku 4.5** for MCQ scoring | Nemotron 3 Ultra | Free-text grading is the highest-judgment step in Mastery Mesh; MCQ scoring is close to deterministic |
| Usage-Signal | **Haiku 4.5** | Nemotron 3 Ultra | High-volume, mostly classification/tagging |
| Correlation | **Opus 5** | Nemotron 3 Ultra | Highest-stakes reasoning — feeds real nudges and rollups, must get the correlation-not-causation framing right every time |
| Nudge Composer | Sonnet 5 | Nemotron 3 Ultra | Tone-sensitive, not deeply analytical; handles both nightly-pulse drafts and admin campaign messages |
| Rollup Reporter | Sonnet 5 | Nemotron 3 Ultra | Narrative synthesis over numbers the Correlation Agent already computed |
| Nudge Category Generator | Sonnet 5 | Nemotron 3 Ultra | Aggregated pattern analysis — moderate reasoning over KPI summaries, no per-practitioner detail |

For the nightly `nightly_pulse` workflow specifically: it's not latency-sensitive, so route it through the **Message Batches API** (structured outputs are fully compatible with it, and it runs at a 50% discount) instead of the synchronous Messages API. That's a real cost lever for a workflow that runs on every practitioner, every night.

**Note:** NVIDIA Nemotron does not support the Message Batches API. When `APP_BRAIN_MODEL=NVIDIA`, the nightly pulse workflow falls back to synchronous execution.

---

## Multi-Model Provider Support (Phase 8)

The system supports two LLM providers selectable at runtime via the `APP_BRAIN_MODEL` environment variable:

| Provider | Env Value | API Key | Base URL | Default Model |
|---|---|---|---|---|
| Anthropic (default) | `ANTHROPIC` | `ANTHROPIC_API_KEY` | `https://api.anthropic.com` | `claude-sonnet-5` |
| NVIDIA Nemotron | `NVIDIA` | `NVIDIA_API_KEY` | `https://integrate.api.nvidia.com/v1` | `nvidia/nemotron-3-ultra-550b-a55b` |

### Abstraction Layer

A unified `ModelClient` protocol in `backend/app/agents/model_client.py` abstracts provider differences. Both `AnthropicModelClient` and `NVIDIAModelClient` implement:

- `messages.parse()` with Structured Outputs (Pydantic model validation)
- Token usage extraction (`input_tokens`, `output_tokens`)
- Latency measurement
- Transient error detection and retry logic

The `Agent` base class accepts any `ModelClient` implementation — no agent code changes required.

### MCP Compatibility

MCP servers use the `anthropic[mcp]` client-side pattern, which is **Anthropic-specific**. When `APP_BRAIN_MODEL=NVIDIA`:

- Agents that use MCP (Skill Profiler, Usage-Signal) log a warning and proceed **without** external MCP data
- Certification Advisor is unaffected (catalog passed in prompt)
- Skill Profiler uses only `skill_profile_events` (no `mcp-learning-portal` data)
- Usage-Signal uses empty raw signals (produces no usage events)

This is a v1 limitation. Future versions may implement a generic tool-calling loop.

### Configuration

Required `.env` variables:

```bash
APP_BRAIN_MODEL=ANTHROPIC  # or NVIDIA
ANTHROPIC_API_KEY=...      # required when ANTHROPIC
NVIDIA_API_KEY=...         # required when NVIDIA
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_MODEL_ID=nvidia/nemotron-3-ultra-550b-a55b
```

---

## Auth & sessions (Step 5.2)

Two roles, two login paths, one cookie — no JWT, no external identity provider.

### Practitioner login
The landing page shows a form: **email** → **name** → **role** → **practice** → **seniority level**. No password. On email blur, the form calls `GET /auth/lookup-email`; if the email is already on record, the remaining fields are pre-filled (user can edit and save). On submit:
1. Backend looks up the practitioner by email in `practitioners`.
2. If not found, creates a new row with the supplied values.
3. If found, all editable fields are overwritten ("save and override" semantics — relaunching with the same email always reflects current org state).
4. A session row is created in `sessions` (`identity_type = practitioner`) and the UUID is returned as an HTTP-only cookie.

This means a practitioner who relaunches the app and re-enters their email gets back to their existing skill snapshots, learning paths, attempts, and certification goals automatically — no account setup, no password.

### Admin / Leadership login
Same landing page. A **"I'm an admin / leadership member"** checkbox (or toggle) reveals a second field: **password**. On submit:
1. Backend looks up the email in `admin_users` (not `practitioners` — completely separate table).
2. Verifies the bcrypt hash against the supplied password.
3. If `must_change_password = true`, creates the session but returns a redirect flag — the frontend sends the user to a forced password-change screen before they reach any data view.
4. On successful first-login password change, sets `must_change_password = false` and `last_login_at`.

Every new `admin_users` row is seeded with password `"welcome"` and `must_change_password = true`. Admins can change their own password at any time from a settings page.

`role` in `admin_users` is either `admin` (full access including individual practitioner detail) or `leadership` (aggregates + rollups only — cannot see individual raw attempts). Both share the same login flow; the distinction is enforced in route middleware, not at login time.

### Session mechanics
- Sessions live in `sessions` (server-side). The browser holds only the opaque UUID in an **HTTP-only** cookie. No `localStorage`, no `sessionStorage` — per `docs/coding-guidelines.md`.
- A FastAPI dependency (`get_session`) reads the cookie on every protected route, loads the session row, and attaches a typed `Session` object to `request.state`. If the cookie is missing or the session row doesn't exist, the dependency returns 401.
- Route-level role guards: practitioner routes return 403 for admin sessions and vice versa; rollup and nudge-approval routes require `admin` or `leadership`.
- Admin sessions expire after inactivity (configurable via `settings.admin_session_timeout_hours`, default 8). Practitioner sessions do not expire — every request updates `last_seen_at`.

### What each role can see

| View | Practitioner | Leadership | Admin |
|---|---|---|---|
| Own skill radar, quiz, adoption trends | ✓ | — | — |
| Own nudge inbox (unread/read messages) | ✓ | — | — |
| Own mastery progress trend chart | ✓ | — | — |
| Other practitioners' individual data | — | — | ✓ (read-only) |
| Rollups (aggregated, privacy-gated) | — | ✓ | ✓ |
| Nudges menu — generate categories, send campaigns | — | — | ✓ |
| Nudges menu — view sent campaign history | — | ✓ | ✓ |
| Observability dashboard (agent_runs) | — | — | ✓ |

## Smart Nudge System (Phase 7)

The nightly `nudge_composer` agent continues to draft automated nudges from Correlation Agent output — that path is unchanged. Phase 7 layers on a second, admin-driven path:

```
Admin clicks "Generate Nudge Categories"
    → GET /nudges/generate-categories
        → query aggregate KPI stats (no PII)
        → NudgeCategoryGenerator agent (Sonnet 5)
        → persist ≤10 NudgeCategory rows
        → return to admin UI

Admin selects a category (or types a custom one)
    → POST /nudges/categories/{id}/preview-recipients
        → resolve_recipients(criteria) — pure Python, no LLM
        → return [{id, name, email, action_profile_summary}]

Admin clicks "Compose message"
    → POST /nudges/categories/{id}/compose
        → Nudge Composer agent (Sonnet 5) — receives category + tone_hint + recipient count, not names
        → return {subject, body, tone_check, recipients}
        → NO DB writes yet — preview only

Admin reviews table, unchecks any practitioners, edits message, clicks Send
    → POST /nudges/send
        → one nudges row per included practitioner (status=sent, sent_at=now, channel=in_app)
        → workflow_runs row under nudge_campaign

Practitioner sees "1 unread" badge on Adoption Trends tab
    → useUnreadNudgeCount polling hook (60s)
    → click card → PATCH /nudges/{id}/read → badge clears
```

**Privacy contract for this flow:** the Nudge Category Generator receives only aggregate counts — no practitioner names, emails, or individual scores. The LLM never sees PII. Individual practitioner data is resolved after the LLM step by `resolve_recipients`, which is a plain Python DB query.

**Tone contract:** the Nudge Composer is responsible for producing encouraging messages. The agent's prompt includes a self-check step (`tone_check`) that the admin sees before sending. See `docs/human-in-the-loop.md` for ownership of the category-generator and composer prompts.

### Folder additions for Step 5.2
- `backend/app/api/routes/auth.py` — `POST /auth/practitioner-login`, `POST /auth/admin-login`, `POST /auth/logout`, `POST /auth/change-password`
- `backend/app/api/deps/session.py` — `get_session` dependency, `require_practitioner`, `require_admin`, `require_admin_or_leadership`
- `frontend/src/pages/LoginPage.tsx` — landing page with practitioner/admin toggle
- `frontend/src/pages/ChangePasswordPage.tsx` — forced first-login password change for admins
- `frontend/src/context/SessionContext.tsx` — React context holding `{ identityType, firstName, practitionerId?, adminRole? }`; populated from `GET /auth/me` on app load; drives the nav bar greeting ("Hi, Ayan") and route guards

---

## Folder structure

```
mastery-pulse/
├── CLAUDE.md
├── project_plan.md
├── docs/
│   ├── architecture.md          (this file)
│   ├── data-model.md
│   ├── coding-guidelines.md
│   └── human-in-the-loop.md
├── backend/
│   ├── pyproject.toml
│   ├── alembic/                  # migrations
│   └── app/
│       ├── main.py                # FastAPI entrypoint
│       ├── config.py
│       ├── db/                    # SQLAlchemy models + session
│       ├── api/routes/            # REST endpoints per resource
│       ├── agents/
│       │   ├── base.py            # Agent contract (Step 0.4)
│       │   ├── certification_advisor.py, skill_profiler.py, curriculum_planner.py,
│       │   │   item_writer.py, grader.py, usage_signal.py, correlation.py,
│       │   │   nudge_composer.py, rollup_reporter.py, nudge_category_generator.py
│       │   └── prompts/           # one .md per agent — see coding-guidelines.md
│       ├── mcp_servers/
│       │   ├── learning_portal/
│       │   └── usage_signals/
│       ├── services/
│       │   └── email.py           # async email via aiosmtplib (Step 7.6)
│       ├── workflows/             # recommend_certification.py, generate_learning_path.py,
│       │                          #   nightly_pulse.py, nudge_campaign.py
│       └── schemas/                # Pydantic I/O contracts
│   ├── seed/                       # synthetic seed data generator
│   └── tests/scenarios/            # Given/When/Then tests — see coding-guidelines.md
└── frontend/
    ├── package.json
    ├── src/
    │   ├── pages/, components/ (CertAdvisor/, SkillRadar/, QuizRunner/, TrendDashboard/,
    │   │                         RollupView/, NudgesPage/, ProgressTrendChart/)
    │   ├── api/                    # typed client
    │   └── hooks/
    └── tests/                       # Playwright scenarios
```
