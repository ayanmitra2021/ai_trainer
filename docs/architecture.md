# Architecture — Mastery Pulse

Reference doc. Read this before building any agent, workflow, or MCP server. Pairs with `docs/data-model.md` (what's stored) and `docs/coding-guidelines.md` (how it's coded).

## The product in one paragraph

Mastery Pulse is one app built from two ideas that share a skill graph. **Mastery Mesh** is the front stage: it profiles a practitioner's skills, builds a personalized learning path, writes and grades practice items (with a trap-reveal mechanic for common misconceptions), and tracks mastery over time. **Adoption Pulse** is the back stage: it watches real usage signals (Claude Code activity, commit patterns) to see whether mastery earned in the front stage shows up in actual work, surfaces the gap, and turns it into individual nudges and leadership rollups. The two halves close a loop: Adoption Pulse's gaps feed back into what the Curriculum Planner prioritizes next.

## The eight agents

Each agent is a single-purpose, typed unit: one input contract, one output contract (a Pydantic model, enforced via Structured Outputs — see below), one row in `agent_runs` per call. An agent never decides on its own to call another agent; a **workflow** (plain Python, not a framework) sequences them. This keeps every agent independently testable and keeps the control flow visible in code instead of hidden inside a graph the human has to reconstruct mentally.

| # | Agent | Job | Reads | Writes |
|---|---|---|---|---|
| 1 | Skill Profiler | Turn raw signals into a current mastery estimate | `skill_profile_events`, MCP: `mcp-learning-portal` | `skill_profile_snapshots` |
| 2 | Curriculum Planner | Pick what a practitioner should work on next | `skill_profile_snapshots`, `correlation_snapshots` | `learning_paths`, `learning_path_items` |
| 3 | Item-Writer | Generate/calibrate practice items, incl. trap-reveal | `items`, `attempts` (calibration stats) | `items` |
| 4 | Grader | Score an attempt, incl. free-text, with rationale | `items`, submitted response | `attempts` |
| 5 | Usage-Signal | Ingest real usage evidence, map it to skill nodes | MCP: `mcp-usage-signals` | `usage_events` |
| 6 | Correlation | Compare "trained" vs. "adopting" per skill | `skill_profile_snapshots`, `usage_events` | `correlation_snapshots` |
| 7 | Nudge Composer | Draft an individual, tone-checked nudge | `correlation_snapshots` | `nudges` (status: `drafted`) |
| 8 | Rollup Reporter | Aggregate, privacy-safe leadership narrative | `correlation_snapshots` (aggregated) | `rollups` |

Two workflows compose them:
- **`generate_learning_path`**: Skill Profiler → Curriculum Planner → Item-Writer (Phase 2)
- **`nightly_pulse`**: Usage-Signal → Correlation → Nudge Composer → Rollup Reporter (Phase 3)

## Agent contract

Every agent implements the same shape (built once, in Step 0.4, then reused seven times):

```python
class Agent(Generic[TInput, TOutput]):
    name: str
    model: str
    output_model: type[TOutput]          # Pydantic model — the Structured Output schema

    async def run(self, input: TInput) -> TOutput:
        ...  # builds prompt, calls Claude, persists an agent_runs row, returns typed output
```

Agents that need external data reach it via MCP tools (below), not by importing another agent's code or hitting the database directly for facts outside their own tables — that boundary is what keeps eight agents from turning into a tangle.

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

No LangGraph/Temporal for v1. A `workflows/` module with plain async functions that call agents in sequence, writing a `workflow_runs` row at start and a status at the end. For a solo-maintained system, "read the Python function top to bottom" beats "reconstruct what a graph framework is doing" every time you need to debug a 2am nightly-job failure. Revisit only if a workflow needs branching complex enough that a hand-rolled sequence becomes the harder-to-read option — none of the two current workflows are there.

## Model selection

Default to **Claude Sonnet 5** (`claude-sonnet-5`) unless a row below says otherwise. Verify against [the current models overview](https://platform.claude.com/docs/en/about-claude/models/overview) before you build each agent — new models ship often enough that this table is a starting point, not gospel, by the time you reach Phase 3.

| Agent | Default | Why |
|---|---|---|
| Skill Profiler | Sonnet 5 | Structured extraction across a few signal sources — moderate reasoning |
| Curriculum Planner | Sonnet 5 | Sequencing/planning, moderate complexity |
| Item-Writer | Sonnet 5 (escalate to **Opus 5** for the hardest trap items) | Pedagogical judgment; most items don't need the top tier |
| Grader | **Opus 5** for free-text/rubric grading; **Haiku 4.5** for MCQ scoring | Free-text grading is the highest-judgment step in Mastery Mesh; MCQ scoring is close to deterministic |
| Usage-Signal | **Haiku 4.5** | High-volume, mostly classification/tagging |
| Correlation | **Opus 5** | Highest-stakes reasoning — feeds real nudges and rollups, must get the correlation-not-causation framing right every time |
| Nudge Composer | Sonnet 5 | Tone-sensitive, not deeply analytical |
| Rollup Reporter | Sonnet 5 | Narrative synthesis over numbers the Correlation Agent already computed |

For the nightly `nightly_pulse` workflow specifically: it's not latency-sensitive, so route it through the **Message Batches API** (structured outputs are fully compatible with it, and it runs at a 50% discount) instead of the synchronous Messages API. That's a real cost lever for a workflow that runs on every practitioner, every night.

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
├── docker-compose.yml            # Postgres for local dev
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
│       │   ├── skill_profiler.py, curriculum_planner.py, item_writer.py,
│       │   │   grader.py, usage_signal.py, correlation.py,
│       │   │   nudge_composer.py, rollup_reporter.py
│       │   └── prompts/           # one .md per agent — see coding-guidelines.md
│       ├── mcp_servers/
│       │   ├── learning_portal/
│       │   └── usage_signals/
│       ├── workflows/             # generate_learning_path.py, nightly_pulse.py
│       └── schemas/                # Pydantic I/O contracts
│   ├── seed/                       # synthetic seed data generator
│   └── tests/scenarios/            # Given/When/Then tests — see coding-guidelines.md
└── frontend/
    ├── package.json
    ├── src/
    │   ├── pages/, components/ (SkillRadar/, QuizRunner/, TrendDashboard/, RollupView/)
    │   ├── api/                    # typed client
    │   └── hooks/
    └── tests/                       # Playwright scenarios
```
