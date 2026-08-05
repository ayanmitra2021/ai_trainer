# Coding Guidelines — Mastery Pulse

Reference doc. Read the relevant section before writing code in that area; you don't need all of this loaded for every step.

## Python (backend)

- Type hints everywhere; Pydantic v2 models for every agent input/output and every API request/response body.
- `ruff` + `black`, default settings. Run before calling a step done.
- Async all the way through the agent/workflow/MCP-client path — that stack is I/O-bound (API calls, DB, subprocess MCP servers) and mixing sync and async there is where subtle bugs live.
- An agent's `run()` method does the Claude call and returns a typed result. It does **not** decide whether to persist — the calling workflow or route does that. This keeps agents testable in isolation without a database.
- No agent imports another agent. If agent B needs something agent A produced, that's the workflow's job to pass along, not agent B reaching sideways.

## Prompts live outside the code

Each agent's system prompt is a separate file — `backend/app/agents/prompts/<agent_name>.md` — loaded at runtime, not an inline Python string. Two reasons this matters here specifically: it's the part of this system you (Ayan) most want to hand-tune directly without touching Python, and it makes prompt changes visible in `git diff` as prose edits instead of buried in code. See `docs/human-in-the-loop.md` — most of the flagged steps are really "own the prompt file for this agent," not "own the Python."

## Reference data goes in the prompt as context, not as knowledge

The certification catalog changes on a timescale of months, not years — providers retire exams, rename tiers, and add new ones. So the Certification Advisor's prompt says, in effect, "here is the current catalog, reason over it," and the current catalog rows are injected into the call every time — never "here's what Anthropic/AWS/Google/Microsoft certifications exist" written into the prompt as if it were a stable fact. The same principle applies anywhere else an agent's job depends on data that goes stale faster than the codebase does: pass it as data, don't write it into the prompt as knowledge.

## TypeScript / React (frontend)

- Strict mode, no `any`. Functional components + hooks, no class components.
- Server state (skill scores, learning paths, rollups) via a typed API client + a query cache (e.g. TanStack Query) — not ad hoc `useEffect` fetching.
- No browser storage (`localStorage`/`sessionStorage`) for anything that matters — React state or the backend, per the artifact/environment constraints that apply project-wide.
- Read `/mnt/skills/public/frontend-design/SKILL.md` before building any new component — it covers the design-token and styling constraints for this environment and keeps the five surfaces (Certification Advisor questionnaire, Skill Radar, Quiz Runner, Trend Dashboard, Rollup View) visually coherent instead of each looking like a separate tutorial.

## Testing: scenario-driven, not unit-driven

Every step in `project_plan.md` ships with Given/When/Then scenarios, not isolated function tests. The pattern is plain `pytest` (backend) and plain Playwright (frontend) — no `pytest-bdd` or `.feature` files. That's a deliberate simplicity choice: `.feature` files plus step-definition glue earn their cost on a team where non-engineers read the scenarios; for a solo build, the overhead isn't worth it. The scenario is written as a docstring on the test itself:

```python
class TestSkillProfilerAgent:
    async def test_new_practitioner_gets_initial_profile_from_certification(
        self, db_session, seeded_practitioner, stub_claude_client
    ):
        """
        Scenario: New practitioner with a completed certification gets an initial profile
          Given a practitioner with no existing skill profile
            and a recorded completion of "RAG Fundamentals" in the Learning Portal
          When the Skill Profiler Agent runs for that practitioner
          Then a skill profile is created
            and the "RAG Fundamentals" node has a mastery_score > 0
            and an agent_runs record links the result to "skill_profiler"
        """
        # Given
        ...
        # When
        result = await SkillProfilerAgent(client=stub_claude_client).run(...)
        # Then
        ...
```

Frontend scenarios follow the same shape with `test.describe` as the feature and Given/When/Then comments inside the `test()` body.

### The one trap to design around from day one: LLM calls aren't deterministic

A "scenario test" that calls the real Claude API on every run is slow, costs money on every CI run, and will occasionally fail for reasons that have nothing to do with your code. The fix, applied from Step 0.4 onward:

- Every scenario test that exercises an agent uses a **stub Claude client fixture** — a fake that returns a fixed, schema-valid response for a given input. This is what almost all scenario tests use; they're testing *your* code (does the workflow persist the right rows, does the API return the right shape), not Claude's reasoning quality.
- A small, separately-marked set of **live** tests (`@pytest.mark.live`) call the real API with real prompts, for the handful of scenarios where you're actually validating prompt quality (especially the human-in-the-loop steps). Run these manually or on a schedule, not on every commit.
- Never assert on exact LLM prose. Assert on structure (`response.mastery_score > 0`, `attempts.count == 1`, enum membership checked case-insensitively) — see the Structured Outputs note in `docs/architecture.md` on why casing isn't perfectly guaranteed.

### Definition of done, per step

A step is done when its scenarios are green against the stub client, not when the code merely runs once. `project_plan.md` states this per step so it's never ambiguous what "done" means before you `/clear` and move on.

## Observability from day one

Every agent call writes an `agent_runs` row (Step 0.4) — model used, tokens, latency, status. Don't treat this as a Phase 5 nice-to-have; without it, debugging why the Correlation Agent produced a weird gap score for one practitioner means re-running things and guessing, instead of reading a row.
