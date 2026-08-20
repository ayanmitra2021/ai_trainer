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
| 2 | Skill Profiler | Turn quiz-attempt signals into broad skill mastery estimates | `skill_profile_events` (source=`quiz_attempt` only, Phase 9.4) | `skill_profile_snapshots`, `mastery_history` |
| 3 | Curriculum Planner | Pick what a practitioner should work on next | `skill_profile_snapshots`, `correlation_snapshots`, `practitioner_certification_goals`, `certification_domains` | `learning_paths`, `learning_path_items` |
| 4 | Item-Writer | Generate/calibrate a single practice item for one skill; used by the auto-refresh path (Step 10.8) when a practitioner exhausts a skill's existing questions; tags items with `certification_domain_id` and `is_cert_evaluated` | `items`, `attempts` (calibration stats), `certification_domains` | `items` |
| 4b | Quiz Batch Generator | Called once per skill in a background task (`_generate_quizzes_progressively`); generates 1–2 questions for that skill (~700-1400 output tokens — fits NVIDIA 90 s budget); exhaustion-aware refresh adjusts difficulty per skill from prior attempt scores; cert-evaluated skills get 2-question slots; per-skill failures are logged and skipped (not fatal); Anthropic Haiku only invoked as fallback when all NVIDIA tiers fail | `skill_profile_snapshots` (mastery), `certification_domains`, `items` (prior prompts, no-repeat), `attempts` (exhaustion check) | `items` |
| 4c | Cert Skill Mapper | Web-research a certification's current exam guide and return 10–12 overarching skills aligned to its official exam domains; persists skills to `certification_skills` with domain linkage; called at profile lock time (if not yet run for this cert) and on demand by admin | `certifications`, `certification_domains` (current version) | `skills` (upsert), `certification_skills` (source=`agent_discovered`) |
| 5 | Grader | Score an attempt, incl. free-text, with rationale | `items`, submitted response | `attempts` |
| 6 | Usage-Signal | Ingest real usage evidence, map it to skill nodes | MCP: `mcp-usage-signals` | `usage_events` |
| 7 | Correlation | Compare "trained" vs. "adopting" per skill | `skill_profile_snapshots`, `usage_events` | `correlation_snapshots` |
| 8 | Nudge Composer | Draft a campaign message (admin-initiated) | `correlation_snapshots`, `nudge_categories` | `nudges` (status: `sent`) |
| 9 | Nudge Category Generator | Analyze aggregate KPI data and propose up to 10 nudge categories with machine-readable criteria | `practitioners`, `skill_profile_snapshots`, `attempts`, `usage_events`, `nudges` (aggregate counts only — no PII) | `nudge_categories` (via API) |
| 10 | Domain Scorer | Map self-assessment proficiency ratings → initial certification domain scores at profile-lock time; also pins the active `certification_domain_version` to the profile | `profile_skill_assessments`, `certification_domains` (filtered to the profile's pinned version), `certification_domain_versions` | `certification_domain_scores` (source=`self_assessment_estimate`); sets `practitioner_profiles.domain_version_id` |
| 11 | Cert Domain Discovery | Research and propose updated exam domain definitions for any certification; called on demand by admin to keep domain data current as exams are revised or new certs are added | `certifications`, `certification_domain_versions` (current version, for comparison), `certification_domains` | `certification_domain_proposals` (status=`pending_review`) → on admin approval: new `certification_domain_versions` + `certification_domains` rows |
| 12 | Byte-Sized Lesson | For one skill gap, generate a short (≤5 min) engaging write-up in Markdown plus 3–5 curated external links (blog posts, official vendor docs, YouTube); called once per skill in a background task after path generation | `skills`, `certification_domains`, `practitioner_profiles` (cert context), current mastery score | `byte_sized_lessons` (status `ready` on success, `failed` on provider error) |

> **Phase 9.1 note:** Agent 9 (Rollup Reporter) has been removed from the active product. The archived implementation lives in `backend/app/agents/_deprecated/rollup_reporter.py`.

Three active workflows compose them:
- **`recommend_certification`**: Certification Advisor alone (Phase 2) — the actual front door for a new practitioner.
- **`generate_learning_path`**: Skill Profiler → Domain Score computation → Curriculum Planner — updates the Skill Radar and domain gap chart. On completion, launches **two** FastAPI background tasks: (1) `_generate_quizzes_progressively` — calls `QuizBatchGeneratorAgent` once per skill (1–2 questions each, Phase 17); (2) `_generate_byte_sized_lessons` — calls `ByteSizedLessonAgent` once per skill gap (Phase 18). Both tasks run independently; per-skill failures in either are isolated (log WARNING, continue). The HTTP response returns before either task finishes. Polling for quiz status and lesson generation_status happens client-side. Skips quiz generation if unanswered items still exist; always regenerates lessons on a new path.
- **`nudge_campaign`**: Nudge Category Generator → Nudge Composer (Phase 7) — admin-initiated; runs on demand, not on a schedule.

The Cert Domain Discovery agent (Phase 10.3) is not part of a workflow — it is invoked directly by admin API endpoints (`POST /admin/cert-domains/discover` and `/discover-all`). Proposals are reviewed and approved/rejected via the Admin UI (Phase 10.4) before any domain data changes.

The Cert Skill Mapper agent (Phase 13.2) is invoked in two ways: (1) automatically during the profile lock call — if no `agent_discovered` skills exist for the cert yet — and (2) on demand by admin via `POST /admin/certs/{cert_id}/discover-skills`. It uses web search to find the current exam guide, then upserts skills directly without a proposal/review step (skills are lower-stakes than domain definitions — incorrect skills are corrected by re-running the mapper, not by reverting a version).

> **Phase 9.1 note:** The `nightly_pulse` workflow (Usage-Signal → Correlation → Nudge Composer → Rollup Reporter) has been removed. Correlation snapshots still feed the admin nudge campaign system, but there is no longer a scheduled automated run.

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

## Byte-Sized Learning (Phase 18)

### What it is

After each path generation, the `ByteSizedLessonAgent` produces one short write-up per skill gap — a crisp, bulleted, fun-to-read micro-article the practitioner can consume in ≤5 minutes. Content is calibrated to the practitioner's current mastery gap and the cert's exam-domain context. At the bottom of each write-up, 3–5 curated external links (official vendor docs, reputable blog posts, YouTube videos) point to deeper reading.

### Where it lives

The Byte-Sized Learning section appears in the **Skill Radar tab**, above the Learning Journey section. It is a table with columns: Skill, Current Gap %, Target %, What You Might Be Missing, Time Spent, and Read (button). Unread lessons have a pulsing left-border glow. Lessons from previous path generations are preserved and shown below a "Previous paths" divider at reduced opacity — nothing is discarded.

### Generation lifecycle (mirrors quiz generation)

| State | Meaning |
|---|---|
| `pending` | Row created; background task not yet reached this skill |
| `ready` | `ByteSizedLessonAgent` succeeded; `content_md` populated |
| `failed` | All provider tiers failed for this skill; surfaced in UI with a Retry link |

Each path regeneration increments `path_generation_seq`. Current lessons (max seq) are the action items; history (prior seq values) is reference.

### Read modal

Clicking "Read" opens a full-screen modal with:
- **Content:** `content_md` rendered as Markdown.
- **Circular clock timer:** SVG ring that fills in over the estimated read time; turns green when the full time is reached.
- **Read Aloud (🔊):** Web Speech API `speechSynthesis` — no external service, no API key. Speed selector: 0.75× / 1× / 1.25× / 1.5× / 2×, matching YouTube's UI convention.
- **External links:** labeled list at the bottom with type icons (📝 blog / 📖 docs / 🎥 video).

### Time-spent tracking

- On modal open: `POST /byte-sized-lessons/{id}/read-sessions` creates a `lesson_reads` row.
- On modal close: `PATCH .../read-sessions/{session_id}` records `duration_seconds`.
- Table display: if `total_read_seconds < 50% of estimated_read_minutes × 60`, the Time Spent column shows "⚡ Read again" (amber); otherwise shows elapsed time (green).

### Read Aloud — no external dependencies

`speechSynthesis` is a browser standard available in Chrome, Edge, Firefox, and Safari. Content is stripped of Markdown syntax before being passed to `SpeechSynthesisUtterance`. The button is hidden silently when `window.speechSynthesis` is undefined (e.g. headless test environments). No backend involvement.

---

## Mock Exam (Phase 11 — updated Phases 18 & 19)

The Mock Exam is always accessible from the Skill Radar tab — **the 80% mastery gate introduced in Phase 11 is removed in Phase 18.** Practitioners are trusted to decide when they are ready to test themselves.

A soft advisory tip is shown when aggregate mastery is below 40%: *"💡 Tip: answering more quizzes first will sharpen your readiness — but you're welcome to try anytime!"* No tip is shown between 40% and 80%.

### Session lifecycle (Phase 19 extended)

```
[POST /mock-exams] → status=generating → [background task generates questions domain-by-domain]
                                       ↓
                              status=in_progress  ←──── resume
                                /       \
                           abandon      pause
                              ↓           ↓
                         abandoned      paused ──── resume ──→ in_progress
                                           ↓
                                       complete
                                           ↓
                                       completed
```

At most one "live" session (`generating`, `in_progress`, `paused`) per practitioner. `completed`, `failed`, and `abandoned` sessions are all retained for history and recycling.

### Question generation — background task with domain-by-domain commits

`POST /mock-exams` returns immediately with `status=generating`. A FastAPI `BackgroundTasks` function `_generate_exam_questions_bg` then:
1. Iterates domains sequentially (not concurrently) — avoids blowing the circuit breaker via simultaneous NVIDIA calls
2. Per domain, calls `_pick_recycled_questions()` first (see below)
3. Calls `MockExamGeneratorAgent` only for remaining slots
4. Commits each domain's batch immediately — frontend polls `GET /mock-exams/{id}` and shows questions as they arrive
5. On completion: transitions to `in_progress`, sets `last_resumed_at`, corrects `total_count`
6. On total failure (all domains failed): transitions to `failed`

Options are shuffled with index remapping at storage time to counter the LLM's positional bias (models consistently place the correct answer at index 0).

### Smart question recycling (Phase 19)

When building a new exam for a domain with `N` question slots:

```
unexercised_pool  = abandoned sessions → questions with response IS NULL, matching domain
                    ordered: newest session first, random within session

remediation_pool  = any prior session → questions with score = 0.0, matching domain
                    ordered: random (mix in for variety)

slots = N
recycled = []

# Step a — unexercised questions get top priority (API-free)
for q in unexercised_pool:
    if slots == 0: break
    recycled.append(copy_and_reshuffle(q))
    slots -= 1

# Step b — remediation questions (up to 30% of N, randomly interspersed)
remedia_cap = max(1, round(N * 0.3))
for q in remediation_pool[:remedia_cap]:
    if slots == 0: break
    recycled.append(copy_and_reshuffle(q))
    slots -= 1

# Step c — LLM call only for remaining slots
if slots > 0:
    new_questions = await MockExamGeneratorAgent.run(batch_size=slots, domain_focus=domain)
    recycled.extend(new_questions)
```

Recycled questions are copied into the new session (new IDs, `response=null`, re-shuffled options) — sessions remain self-contained.

### Abandonment (Phase 19)

`POST /mock-exams/{session_id}/abandon` requires a non-empty `reason` string. Sets `status='abandoned'`, `abandoned_at`, and `abandoned_reason`. The active-session guard allows a new session to be started immediately after abandonment. Abandoned sessions appear in the history table with their reason visible.

### Mock Exam History table (Adoption Trend tab — Phase 19)

All sessions for a practitioner are listed newest-first: date, certification, status (colour-coded), score %, questions answered / total, time spent, abandon reason (if applicable). For the single live session (if any), an "Abandon" button opens a dialog requiring a non-empty reason before confirming.

### Exam Confidence Score (Adoption Trend tab — Phase 19)

Computed client-side from the practitioner's `completed` session history:

```
weight(i) = 2^i / Σ(2^j for j in 0..n-1)   # most-recent exam has highest weight
            where i=0 is the oldest, i=n-1 is the newest

weighted_avg = Σ(weight(i) × session[i].score)

confidence_pct = round(weighted_avg × 100)
```

Displayed as a circular progress gauge showing `confidence_pct` vs. `exam_passing_score_pct`. A trend arrow (↑ / ↓ / →) compares the last two exams. An "Exam Ready" badge appears when `weighted_avg ≥ exam_passing_score_pct / 100` and there are at least 2 completed exams. No score shown if there are 0 completed exams ("No exams completed yet").

---

## Certification-Domain Alignment (Phase 10)

**The core principle:** skills, scores, and gaps must be rooted in the actual exam domains of the practitioner's chosen certification — not in arbitrary catalog skills or generic proficiency areas. This is what makes exam readiness meaningful rather than decorative.

### Why two tiers

The product maintains two parallel scoring dimensions that serve different purposes:

| Dimension | What it shows | Driven by | Where it appears |
|---|---|---|---|
| **Skill Radar** | Broad, evolving knowledge across ~10–15 overarching skills | All quiz answers (cert-evaluated AND supplementary) | Radar polygon, mastery trend chart |
| **Domain Gap Chart** | Exam-specific readiness across the certification's official exam domains | Cert-evaluated quiz answers only (`is_cert_evaluated = true`) | Gap bar chart below the radar |

A practitioner who answers a "good to know" question correctly grows their radar but does not move their exam-domain readiness score. Only questions tagged `is_cert_evaluated = true` — items that map directly to the certification's official exam blueprint — improve the domain gap chart.

### Mandatory certification at profile creation

A practitioner profile **cannot be created without a certification associated** (`practitioner_profiles.certification_id` is NOT NULL from Phase 10.1 onward). The certification choice is the anchor that makes everything else in the system meaningful: it determines which exam domains to load, which quiz items to generate, and what the domain gap chart measures.

### Domain versioning — why domain data is live-refreshable (Phase 10.2–10.4)

AI certification exams change faster than seed files get updated. AWS retired its ML Specialty exam and replaced it with MLA-C01 in the same window this project was built; Google Cloud adds new credentials quarterly; Anthropic's CCAR-P credential didn't exist six months before it was added to the catalog. A hardcoded `certification_domains.py` that requires a code change and redeploy to update would go stale within one exam revision cycle (typically 6–12 months), silently producing quiz items for domains that no longer exist at the weights the exam currently assigns.

**The solution: `certification_domain_versions`.** Each set of official domain definitions for a certification is a version row. The bootstrap seed from Phase 10.1 creates version 1 for each cert. From Phase 10.3 onward, an admin can trigger the Cert Domain Discovery Agent to research and propose updated domains; on approval, a new version is published without touching old rows.

**Freeze semantics:** `practitioner_profiles.domain_version_id` is set at profile-lock time (Phase 10.5) to the cert's currently-active version. All domain scoring for that profile — initial self-assessment estimates (Domain Scorer Agent), quiz-derived scores (`compute_domain_scores`), and gap chart queries — use the `certification_domains` rows filtered to that pinned version. A subsequent admin refresh creates a new version; existing profiles are never retroactively shifted. New profiles inherit the latest version automatically.

**New cert discovery:** the Cert Domain Discovery Agent can propose a certification that doesn't yet exist in the catalog. Approving such a proposal creates a `certifications` row with `is_active = false` and its first `certification_domain_versions` row. The admin must separately activate the cert (via the existing certs API) before it becomes selectable by practitioners.

### Item tagging (`is_cert_evaluated`)

Every item in the bank carries two domain-alignment fields:
- `certification_domain_id` — which of the cert's official exam domains this item tests
- `is_cert_evaluated` — `true` if the topic is directly tested in the exam; `false` for supplementary items that build conceptual understanding but aren't in the exam blueprint

The Item-Writer Agent receives the active cert's domain list and generates items that span all domains. It tags each item based on whether the topic appears in the official exam guide. 👤 The judgment call ("does this concept appear in the exam guide?") is encoded in `prompts/item_writer.md` — see `docs/human-in-the-loop.md`.

### Domain Scorer Agent (Phase 10.2)

At profile-lock time, the Domain Scorer Agent bridges the gap between the practitioner's self-assessment (generic proficiency ratings) and the cert's official domains. It receives the self-assessment skill ratings plus the cert's domain descriptions and reasons about the mapping: "a practitioner who rates themselves Advanced in Prompt Engineering likely has initial domain-level readiness in Domain 2: Fundamentals of Generative AI."

This provides a non-zero starting baseline in the domain gap chart — better than forcing every new practitioner to start from 0% before they've taken a single quiz. The estimate carries a confidence cap of 0.5 (never more than halfway confident based on self-assessment alone). The first cert-evaluated quiz answer for any domain immediately sets `source = 'quiz_derived'`, which takes full precedence over the estimate.

### Quiz UI: color-coded cert relevance (Phase 10.5)

Each quiz item card displays a relevance badge:
- **"📋 Exam relevant"** (blue) — `is_cert_evaluated = true`; answering this moves the domain readiness score
- **"💡 Good to know"** (grey) — `is_cert_evaluated = false`; answering this builds understanding but doesn't move domain readiness

The skill selector tabs are ordered: cert-domain skills first (with a colored "Exam" pill), supplementary skills below a section divider. This lets practitioners choose whether to focus their session on exam-critical topics or broader understanding.

---

## Quiz Generation Strategy (Phase 12)

### Why question generation is background and per-skill (Phase 12 → Phase 17)

A certification path has at most ~16 skills. Questions must be available immediately after path generation — but generating 10–12 full MCQs (with `correct_rationale`, `incorrect_rationale`, `trap_explanation`) in a **single LLM call** produces 8–12K output tokens, which consistently exceeds NVIDIA's timeout budgets (90 s Ultra, 45 s Lightning) even after tuning. Calling Anthropic as a primary shortcut to avoid the timeouts would undermine the cost constraint (Haiku is the emergency fallback, not the default).

The Phase 17 solution: the path generation HTTP response returns immediately after the Profiler + Planner complete (~30 s); a FastAPI **background task** then generates questions **one skill at a time**. Each per-skill call produces 1–2 questions (~700–1400 output tokens) — well within NVIDIA's 90-second window.

| User action | What the system does | Time |
|---|---|---|
| Click "Generate path" | Profiler + Planner run; background task starts | **< 35 s** (HTTP response) |
| Open Quiz tab immediately | Shows questions for skills already done; ⏳ badge for skills still being generated | **< 1 s** |
| Skills finish generating | Quiz tab polls every 5 s; new questions appear without page refresh | **~45-90 s per skill on NVIDIA** |
| All path skills have questions | Polling stops; all skill tabs show their questions | — |
| Answer all questions, click "Regenerate path" | Background task restarts with difficulty-adjusted specs (harder for high scorers, easier for low scorers) | same as above |

### QuizBatchGeneratorAgent — one skill per call

The agent is called once per skill (not once for all skills). `SkillQuizSpec.question_count` (1 or 2) tells it how many items to produce for that skill. With a single spec per call:
- Input: one `{skill_id, skill_name, mastery_score, question_count, prior_prompts, cert_domain, ...}`
- Output: 1 or 2 `BatchQuizItem` objects for that skill, each with `correct_rationale` + `incorrect_rationale` (Phase 16) and `trap_explanation`
- `max_tokens = 3000` — covers 2 questions comfortably; tells NVIDIA not to reserve excess compute time

The background task `_generate_quizzes_progressively` iterates the skill list in order, calling the agent once per skill. Per-skill failures (e.g., one skill's call exhausts all provider tiers) are **logged and skipped** — other skills continue generating. Each skill's questions are persisted immediately after that call succeeds, so the frontend can display them without waiting for the full batch.

### Difficulty calibration across skills

The agent calibrates question difficulty per skill using the practitioner's current `mastery_score`:

| Mastery | Target difficulty | Intent |
|---|---|---|
| 0–25% | 0.30–0.45 | Foundation check — build confidence, confirm basics |
| 25–55% | 0.45–0.65 | Solidifying — apply concepts, spot common mistakes |
| 55–80% | 0.65–0.80 | Challenge — nuanced scenarios, edge cases |
| 80%+ | 0.80–0.95 | Exam-hard — same difficulty as mock exam questions |

On exhaustion-aware refresh, `mastery_score` is adjusted before the spec is built:
- avg_score ≥ 1.0 → mastery += 0.25 (harder questions for skills the practitioner aced)
- avg_score < 0.5 → mastery −= 0.10 (easier questions for skills they struggled with)

### Loading UX — three states per skill

The Quiz tab is immediately usable after path generation. Each skill tab shows one of three states based on `learning_path_items.quiz_status` and the presence of items in the `items` table:

| State | DB condition | Tab appearance |
|---|---|---|
| **Ready** | Items exist for this skill | Normal colour; questions rendered inline |
| **Pending** | `quiz_status='pending'`, no items yet | ⏳ Dimmed; "Questions being prepared…" |
| **Failed** | `quiz_status='failed'`, no items | ⚠️ Amber; "Generation failed for this skill" |

The background task sets `quiz_status='ready'` on success or `'failed'` on `AllProvidersUnavailableError` (or any other exception). Per-skill failures are isolated — other skills continue generating.

The frontend polls `GET /items` and the active learning path every 5 seconds. Polling stops once every skill is either `ready` or `failed` (no `pending` skills remain, or a 5-minute ceiling is hit).

### Retry for failed skills

When any skill is in `failed` state, a **"↻ Retry Failed Skills"** button appears at the top of the skill-tab group. Clicking it calls:

```
POST /practitioners/{id}/quiz-generation/retry
```

This endpoint: fetches the active path → selects all `learning_path_items` with `quiz_status='failed'` → resets them to `'pending'` → fires `_generate_quizzes_progressively` as a new background task for only those skills → returns `{"retried": N}` immediately. The frontend then invalidates its cache to pick up the new `pending` statuses and resumes polling.

The endpoint is idempotent: if no skills are in `failed` state it returns `{"retried": 0}` without launching a task.

---

## Dynamic Cert Skill Mapping (Phase 13)

### Why cert skills cannot be statically seeded

The `certification_skills` table was originally populated by migration seed files — a fixed set of skills per cert, written once and updated manually. This breaks in three ways as exam blueprints evolve:

1. **Staleness.** Cert providers revise domain weights quarterly to yearly. A seed file captures a moment in time and drifts silently.
2. **Sparseness.** Five skills for five domains (1:1) produces quiz tabs that are almost entirely generic. Official exam blueprints describe three to five knowledge areas per domain — 10–12 skills is the right granularity for a 5-domain cert.
3. **Catalog pollution.** The Curriculum Planner draws from the full `skills` catalog. Without a tight cert-specific skill set, it pads paths with generic skills (Prompt Engineering, AI Foundations) that don't move exam-domain readiness scores.

### CertSkillMapperAgent — design

The agent takes the cert's name, code, and current domain list (from `certification_domains`) as input, runs web searches against the official exam guide, and returns 10–12 skills with domain linkage. The `certification_skills` table stores these with `source = 'agent_discovered'`, distinguished from the old `'seed'` rows. Agent-discovered rows are replaced on each re-run; seed rows are never touched.

**Trigger points:**
- **At profile lock** — after the Domain Scorer Agent, before returning. If no `agent_discovered` skills exist for the cert, the mapper runs (60 s timeout; timeout does not fail the lock).
- **On admin demand** — `POST /admin/certs/{cert_id}/discover-skills`. Replaces existing `agent_discovered` skills with the freshest blueprint data.

**Fallback:** if the mapper has not yet run (e.g. seed-only cert, timed-out first lock), the Curriculum Planner and Quiz Batch Generator fall back to `'seed'` rows. No breakage — just less precise cert alignment until the mapper completes.

### Skill sourcing precedence (runtime)

| Code location | Behaviour |
|---|---|
| `generate_learning_path.py` cert context | Prefer `source='agent_discovered'` rows; fall back to `source='seed'` |
| `quiz-batch` endpoint `is_cert_evaluated` lookup | Same precedence |
| Domain-colored radar response | Joins `certification_skills` → `certification_domains`; skips if no domain link |

### Domain-weighted Skill Radar (Phase 13.4)

Radar nodes are colored by the exam-domain weight of the skill's primary domain:

| Domain weight | Node color | Intent |
|---|---|---|
| Highest (e.g. 25%) | Dark blue `#1a56db` | Highest-priority skills — most likely tested |
| Mid-range (e.g. 20%) | Medium blue `#3b82f6` | Important — worth sustained focus |
| Lowest (e.g. 15%) | Light blue `#93c5fd` | Required but less heavily weighted |
| Supplementary (no domain) | Neutral grey `#9ca3af` | Useful context, not on exam |

A domain legend appears below the radar (color swatch + domain name + weight %).  The color encoding is stable across radar re-renders — domain weight doesn't change between path generations.  When no agent-discovered skills exist yet, the radar remains monochrome.

### 80/20 quiz split enforcement (Phase 13.5)

The structural constraint is enforced by the Curriculum Planner's `supp_max` formula. With 10–12 cert skills: `supp_max = max(1, round(10 × 0.2)) = 2` supplementary slots → ≥83% cert questions in the batch. The QuizBatchGeneratorAgent computes and returns `cert_question_pct` / `supp_question_pct` on every call. The quiz-batch endpoint logs a WARNING (never an exception) if `cert_question_pct < 80`.

---

## Multi-Model Provider Support (Phase 8)

The system supports two LLM provider orientations selectable at runtime via the `APP_BRAIN_MODEL` environment variable.  Within each orientation, a three-tier fallback chain (Phase 15) automatically routes to the next available model on any failure.

| Mode | Tier 1 | Tier 2 | Tier 3 |
|---|---|---|---|
| `APP_BRAIN_MODEL=NVIDIA` | Nemotron Ultra (10 s) | Nemotron Lightning (20 s) | Haiku (20 s) |
| `APP_BRAIN_MODEL=ANTHROPIC` | Haiku (10 s) | Nemotron Ultra (20 s) | Nemotron Lightning (20 s) |

> **Model constraint (this deployment):** all Anthropic calls are pinned to `claude-haiku-4-5-20251001`.  The `APP_ANTHROPIC_MODEL_ID` env var (default `claude-haiku-4-5-20251001`) controls this.  Do not change it to Sonnet, Opus, or Fable without explicit approval.  Individual agent `model` class attributes are intentionally ignored by both `AnthropicModelClient` and `NVIDIAModelClient`; each client always uses its own configured `_model_id`.

### Abstraction Layer

A unified `ModelClient` protocol in `backend/app/agents/model_client.py` abstracts provider differences. Client types (`AnthropicModelClient`, `NVIDIAModelClient`, `MultiTierModelClient`) all implement:

- `parse()` with Structured Outputs (Pydantic model validation)
- Token usage extraction (`input_tokens`, `output_tokens`)
- Latency measurement

The `Agent` base class accepts any `ModelClient` implementation — no agent code changes required when the tier chain or provider order changes.

### MCP Compatibility

MCP servers use the `anthropic[mcp]` client-side pattern, which is **Anthropic-specific**. When `APP_BRAIN_MODEL=NVIDIA`:

- Agents that use MCP (Skill Profiler, Usage-Signal) log a warning and proceed **without** external MCP data
- Certification Advisor is unaffected (catalog passed in prompt)
- Skill Profiler uses only `skill_profile_events` (no `mcp-learning-portal` data)
- Usage-Signal uses empty raw signals (produces no usage events)

This is a v1 limitation. Future versions may implement a generic tool-calling loop.

### Configuration

Required `.env` variables (Phase 15):

```bash
APP_BRAIN_MODEL=NVIDIA           # or ANTHROPIC
NVIDIA_API_KEY=nvapi-...
NVIDIA_MODEL_ID_PRIMARY=nvidia/nemotron-3-ultra-550b-a55b
NVIDIA_MODEL_ID_SECONDARY=nvidia/nemotron-3.5-lightning-30b-a3b
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
ANTHROPIC_API_KEY=sk-ant-...
APP_ANTHROPIC_MODEL_ID=claude-haiku-4-5-20251001
# Optional — tuning
NVIDIA_TIER1_TIMEOUT_SECS=10
NVIDIA_TIER2_TIMEOUT_SECS=20
ANTHROPIC_TIER_TIMEOUT_SECS=20
NVIDIA_CIRCUIT_BREAKER_THRESHOLD=5
NVIDIA_CIRCUIT_BREAKER_COOLDOWN_SECS=120
```

---

## Provider Resilience (Phases 14 & 15)

### Three-tier call chain (Phase 15)

Every `Agent.run()` call passes through `MultiTierModelClient`, which tries each tier in order and moves to the next on any failure (timeout or exception).

```
Agent.run()
  └─ MultiTierModelClient.parse()                [APP_BRAIN_MODEL=NVIDIA]
       ├─ [Tier 1] NVIDIAModelClient(Ultra)       10 s timeout
       │      success → return; model_used = nvidia/nemotron-3-ultra-550b-a55b
       │      failure → WARNING: "Primary provider failed (Ultra) — trying next tier"
       │
       ├─ [Tier 2] NVIDIAModelClient(Lightning)   20 s timeout
       │      success → return; model_used = nvidia/nemotron-3.5-lightning-30b-a3b
       │      failure → WARNING: "Primary provider failed (Lightning) — trying next tier"
       │
       └─ [Tier 3] AnthropicModelClient(Haiku)    20 s timeout
              success → return; model_used = claude-haiku-4-5-20251001
              failure → raise AllProvidersUnavailableError(errors=[e1, e2, e3])
```

**Max wall time (all fail):** 10 + 20 + 20 = **50 seconds.**

`MultiTierModelClient` is transparent to agents — they call `.parse()` and receive a result or `AllProvidersUnavailableError`.  The `effective_model` property on `Agent` reflects whichever tier responded, so `agent_runs.model_used` is always truthful.

### In-memory circuit breaker (Phase 15)

The circuit breaker prevents paying the 10 s + 20 s NVIDIA timeout cost on every request during a sustained outage.

```
NvidiaCircuitBreaker (module-level singleton)
  CLOSED  ─── both NVIDIA tiers fail ×N calls ──► OPEN (cooldown 2 min)
  OPEN    ─── all calls skip to Haiku directly ──► CLOSED (after cooldown)
  CLOSED  ◄── at least one NVIDIA tier succeeds → consecutive_failures = 0
```

Threshold and cooldown are configurable via `NVIDIA_CIRCUIT_BREAKER_THRESHOLD` and `NVIDIA_CIRCUIT_BREAKER_COOLDOWN_SECS`.  The breaker lives in process memory and resets on server restart.

### Graceful degraded domain scoring (Phase 14, extended by 15)

When `AllProvidersUnavailableError` reaches the profile-lock endpoint (the Domain Scorer call), the endpoint catches it and computes domain scores mechanically:

1. For each cert domain, average the `signal_strength` values from `profile_skill_assessments` for skills linked to that domain via `certification_skills`.
2. Cap each score at 0.5 (same confidence ceiling as LLM-derived estimates).
3. Write `certification_domain_scores` rows with `source = 'degraded_estimate'` and `confidence = 0.3`.
4. Set `practitioner_profiles.domain_scoring_status = 'degraded'`.
5. Commit and return HTTP 200.  The practitioner's profile locks normally.

For all other endpoints (grader, quiz batch generator, etc.) where no mechanical fallback exists, `AllProvidersUnavailableError` produces **HTTP 503** with a structured body:

```json
{
  "error": "all_providers_unavailable",
  "message": "Our AI services are temporarily unavailable. Your progress is saved — please try again in a few minutes.",
  "retry_after_seconds": 120
}
```

The frontend shows a toast/banner with a Retry button when it receives this body.

### `domain_scoring_status` values

| Value | Meaning |
|---|---|
| `pending` | Domain Scorer has not run yet (default for new profiles; transitional state) |
| `lm_scored` | Domain Scorer ran successfully via any LLM tier |
| `degraded` | All providers failed; scores computed mechanically from self-assessment |

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
- Route-level role guards: practitioner routes return 403 for admin sessions and vice versa; nudge-approval routes require `admin` or `leadership`.
- Admin sessions expire after inactivity (configurable via `settings.admin_session_timeout_hours`, default 8). Practitioner sessions do not expire — every request updates `last_seen_at`.

### What each role can see

| View | Practitioner | Leadership | Admin |
|---|---|---|---|
| Own skill radar, quiz, adoption trends | ✓ | — | — |
| Own nudge inbox (unread/read messages) | ✓ | — | — |
| Own mastery progress trend chart | ✓ | — | — |
| Other practitioners' individual data | — | — | ✓ (read-only) |
| Nudges menu — generate categories, send campaigns | — | — | ✓ |
| Nudges menu — view sent campaign history | — | ✓ | ✓ |
| Observability dashboard (agent_runs) | — | — | ✓ |

> **Phase 9.1:** Leadership rollup reports (the "Rollups" row) have been removed from the product. Leadership users can navigate to `/nudges` to see sent campaign history.

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

## Interactive User Guide (Phase 20)

### What it is

A fully static, client-side documentation page reachable at `/guide` from the nav bar. All authenticated users (practitioners and admins) see the "Guide" nav link. The page is a two-column layout — fixed left sidebar with section navigation, scrollable right pane with content — modelled after the clarity of Anthropic and AWS documentation sites but with original design.

**No backend, no API calls.** The guide is entirely static React. Its content is hardcoded in the component. No routes, no migrations, no LLM calls — it costs nothing at runtime and is never affected by provider outages.

### Content structure

Each section opens with a **Quick Read card** (2-minute summary with ⚡ icon) followed by full detailed content. Sections are anchor-linked from the sidebar.

| # | Section | Visible to |
|---|---|---|
| 1 | Getting Started | All users |
| 2 | Your Skill Radar | All users |
| 3 | Quizzes | All users |
| 4 | Byte-Sized Learning | All users |
| 5 | Mock Exams | All users |
| 6 | Adoption Trends & Nudges | All users |
| 7 | Managing Practitioners | Admin only |
| 8 | Nudge Campaigns | Admin only |
| 9 | Cert Domain Management | Admin only |
| 10 | Observability | Admin only |
| 11 | Admin Users | Admin only |

Admin-only sections (7–11) are rendered only when `session.identity_type === "admin"`, driven entirely by the existing `useSession()` hook. No API call is made; the check is client-side only.

### "Ask Ayan" chat widget

A floating action button (`fixed; bottom: 2rem; right: 2rem`) opens a compact chat panel. Questions are answered by a synchronous `respondToQuestion(text)` function — a keyword-match lookup over ~10 topic clusters. Off-topic queries receive one of ~8 rotating funny responses. Zero API calls, zero LLM involvement.

The widget lives at `frontend/src/components/Guide/AskAyanChat.tsx` and is imported only by `GuidePage`.

### Files introduced by Phase 20

```
frontend/src/
├── pages/
│   └── GuidePage.tsx          # main page — sidebar + content
└── components/
    └── Guide/
        └── AskAyanChat.tsx    # floating chat widget (static keyword matching)
```

`frontend/src/App.tsx` gains one new route (`/guide`) and one new `NavLink` in `NavBar`.

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
