# Multi-Provider Migration Guide

This guide explains the LLM provider strategy for Mastery Pulse: a three-tier fallback chain across two NVIDIA Nemotron models and Anthropic Haiku, with an in-memory circuit breaker that eliminates repeated timeout costs during sustained NVIDIA outages.

> **Anthropic model constraint (this deployment):** all Anthropic calls — regardless of context — use `claude-haiku-4-5-20251001` only.  No Sonnet, Opus, or Fable.  The `APP_ANTHROPIC_MODEL_ID` env var enforces this; `AnthropicModelClient` ignores whatever model string individual agents carry and always calls its configured `_model_id`.

## Quick Start

### Production (NVIDIA primary + Haiku fallback — recommended)

```bash
# In your .env file:
APP_BRAIN_MODEL=NVIDIA
NVIDIA_API_KEY=nvapi-your-key-here
NVIDIA_MODEL_ID_PRIMARY=nvidia/nemotron-3-ultra-550b-a55b
NVIDIA_MODEL_ID_SECONDARY=nvidia/nemotron-3.5-lightning-30b-a3b
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1

# Anthropic Haiku — last-resort fallback (billed; Haiku only)
ANTHROPIC_API_KEY=sk-ant-your-key-here
APP_ANTHROPIC_MODEL_ID=claude-haiku-4-5-20251001

# Optional — tune timeouts and circuit breaker
NVIDIA_TIER1_TIMEOUT_SECS=10
NVIDIA_TIER2_TIMEOUT_SECS=20
ANTHROPIC_TIER_TIMEOUT_SECS=20
NVIDIA_CIRCUIT_BREAKER_THRESHOLD=5
NVIDIA_CIRCUIT_BREAKER_COOLDOWN_SECS=120
```

### Local dev (Anthropic Haiku primary + NVIDIA fallback)

```bash
# In your .env file:
APP_BRAIN_MODEL=ANTHROPIC
ANTHROPIC_API_KEY=sk-ant-your-key-here
APP_ANTHROPIC_MODEL_ID=claude-haiku-4-5-20251001

# Optional — NVIDIA models as fallback when Haiku fails
NVIDIA_API_KEY=nvapi-your-key-here
NVIDIA_MODEL_ID_PRIMARY=nvidia/nemotron-3-ultra-550b-a55b
NVIDIA_MODEL_ID_SECONDARY=nvidia/nemotron-3.5-lightning-30b-a3b
```

## Three-Tier Call Chain (Phase 15)

Every agent call flows through `MultiTierModelClient`, which tries each tier in sequence and only moves to the next on failure (timeout or any exception).

### NVIDIA-primary mode (`APP_BRAIN_MODEL=NVIDIA`)

```
Tier 1 — NVIDIAModelClient(Ultra)       10 s timeout, 1 attempt
  │  success → return; model_used = nvidia/nemotron-3-ultra-550b-a55b
  ↓  any failure — WARNING logged
Tier 2 — NVIDIAModelClient(Lightning)   20 s timeout, 1 attempt
  │  success → return; model_used = nvidia/nemotron-3.5-lightning-30b-a3b
  ↓  any failure — WARNING logged
Tier 3 — AnthropicModelClient(Haiku)    20 s timeout, 1 attempt
  │  success → return; model_used = claude-haiku-4-5-20251001
  ↓  any failure — WARNING logged
AllProvidersUnavailableError raised
  → domain scorer endpoint: mechanical degraded scores (HTTP 200)
  → all other endpoints: HTTP 503 with retry hint
```

**Max wall time (all fail):** 10 + 20 + 20 = **50 seconds.**

### ANTHROPIC-primary mode (`APP_BRAIN_MODEL=ANTHROPIC`)

The tier order is reversed.  Haiku is tried first; the NVIDIA models are the fallback.  Ultra is tried before Lightning because it produces higher-quality output; Lightning is the last resort within the NVIDIA estate.

```
Tier 1 — AnthropicModelClient(Haiku)    10 s timeout, 1 attempt
  ↓  any failure
Tier 2 — NVIDIAModelClient(Ultra)       20 s timeout, 1 attempt
  ↓  any failure
Tier 3 — NVIDIAModelClient(Lightning)   20 s timeout, 1 attempt
  ↓  any failure
AllProvidersUnavailableError raised
```

The circuit breaker (below) does **not** activate in ANTHROPIC mode — NVIDIA is already the fallback, and skipping it entirely would remove a useful safety net.

## Circuit Breaker (Phase 15)

When NVIDIA is experiencing a sustained outage, paying the 10 s + 20 s timeout cost on *every* call is wasteful and makes the app feel slow.  The circuit breaker eliminates this cost during confirmed outages.

### State machine

```
CLOSED (normal)
  │  both NVIDIA tiers fail on the same call → consecutive_failures += 1
  │  consecutive_failures reaches threshold (default 5)
  ↓
OPEN (cooldown)  ←  open_until = now + cooldown_seconds (default 120)
  │  all calls skip NVIDIA tiers; Haiku is used directly
  │  open_until reached
  ↓
CLOSED (reset)   ←  consecutive_failures = 0; resume full chain
```

### What counts as a failure

- Both Tier 1 (Ultra) **and** Tier 2 (Lightning) fail on the same call.
- A call where Tier 1 fails but Tier 2 succeeds does **not** increment the counter — the NVIDIA estate is partially healthy.

### Logs

| Event | Level | Message |
|---|---|---|
| Tier N fails | WARNING | `Primary provider failed (model-id) — trying next tier. Error: …` |
| Breaker trips | WARNING | `NVIDIA circuit breaker tripped after 5 consecutive failures — 2-min cooldown until HH:MM:SS` |
| Breaker active | INFO | `NVIDIA circuit breaker open — routing directly to Haiku (resets at HH:MM:SS)` |
| Breaker resets | INFO | `NVIDIA circuit breaker reset — resuming normal tier chain` |

### Persistence

The breaker lives in process memory only.  A server restart resets it — intentional, because restarts are deliberate interventions that usually coincide with the outage clearing.

## Configuration Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `APP_BRAIN_MODEL` | Yes | `ANTHROPIC` | Primary tier: `ANTHROPIC` or `NVIDIA` |
| `ANTHROPIC_API_KEY` | When Anthropic primary or Haiku fallback needed | — | Anthropic API key |
| `APP_ANTHROPIC_MODEL_ID` | No | `claude-haiku-4-5-20251001` | **Haiku only** — do not change |
| `NVIDIA_API_KEY` | When either NVIDIA model is in use | — | NVIDIA NIM API key |
| `NVIDIA_BASE_URL` | No | `https://integrate.api.nvidia.com/v1` | NVIDIA endpoint (OpenAI-compatible) |
| `NVIDIA_MODEL_ID_PRIMARY` | No | `nvidia/nemotron-3-ultra-550b-a55b` | Ultra — Tier 1 in NVIDIA mode, Tier 3 in ANTHROPIC mode |
| `NVIDIA_MODEL_ID_SECONDARY` | No | `nvidia/nemotron-3.5-lightning-30b-a3b` | Lightning — Tier 2 in both modes |
| `NVIDIA_TIER1_TIMEOUT_SECS` | No | `10` | Timeout for first tier (Ultra or Haiku) |
| `NVIDIA_TIER2_TIMEOUT_SECS` | No | `20` | Timeout for second tier (Lightning) |
| `ANTHROPIC_TIER_TIMEOUT_SECS` | No | `20` | Timeout for Haiku (any position in chain) |
| `NVIDIA_CIRCUIT_BREAKER_THRESHOLD` | No | `5` | Consecutive NVIDIA-only failures before cooldown |
| `NVIDIA_CIRCUIT_BREAKER_COOLDOWN_SECS` | No | `120` | Cooldown duration in seconds |

> **Deprecated (Phase 14 → 15):** `NVIDIA_MODEL_ID` (singular) is replaced by `NVIDIA_MODEL_ID_PRIMARY` and `NVIDIA_MODEL_ID_SECONDARY`.  Remove it from `.env` when upgrading.

## Render Production Env-Var Checklist

Set these in the Render dashboard (Environment → Environment Variables) before the first deploy:

| Variable | Example value | Notes |
|---|---|---|
| `APP_BRAIN_MODEL` | `NVIDIA` | Primary provider |
| `NVIDIA_API_KEY` | `nvapi-...` | From NVIDIA NIM dashboard |
| `NVIDIA_MODEL_ID_PRIMARY` | `nvidia/nemotron-3-ultra-550b-a55b` | Verify against current NIM catalog |
| `NVIDIA_MODEL_ID_SECONDARY` | `nvidia/nemotron-3.5-lightning-30b-a3b` | Lightning fallback within NVIDIA |
| `NVIDIA_BASE_URL` | `https://integrate.api.nvidia.com/v1` | Only override if NVIDIA changes endpoint |
| `ANTHROPIC_API_KEY` | `sk-ant-...` | **Required for Haiku tier** — without this, all-providers-unavailable degrades to mechanical scores only |
| `APP_ANTHROPIC_MODEL_ID` | `claude-haiku-4-5-20251001` | Haiku only — do not change |
| `NVIDIA_CIRCUIT_BREAKER_THRESHOLD` | `5` | Tune down to 3 if you prefer faster failover |
| `NVIDIA_CIRCUIT_BREAKER_COOLDOWN_SECS` | `120` | 2-minute cooldown |
| `DATABASE_URL` | (Supabase connection string) | From Supabase project settings |
| `SECRET_KEY` | (random 32-byte hex) | Generate with `openssl rand -hex 32` |

## Known Limitations (v1)

### MCP Server Compatibility

MCP servers use the `anthropic[mcp]` client-side pattern, which is **Anthropic-specific**. When using NVIDIA:

| Agent | Behavior with NVIDIA |
|-------|---------------------|
| Certification Advisor | Unaffected — catalog passed in prompt |
| Skill Profiler | Uses only `skill_profile_events` (no `mcp-learning-portal` data). Logs warning. |
| Usage-Signal | Uses empty raw signals (produces no usage events). Logs warning. |
| All other agents | Unaffected — no MCP dependency |

**Workaround**: For production NVIDIA deployments requiring MCP data, pre-fetch data externally and pass it via agent inputs.

### Message Batches API

The `nightly_pulse` workflow uses the Anthropic Message Batches API for 50% cost savings. **NVIDIA does not support this API**. When `APP_BRAIN_MODEL=NVIDIA`, the workflow falls back to synchronous execution (2× cost, same functionality).

## Agent Model Mappings

> `AnthropicModelClient` always calls `APP_ANTHROPIC_MODEL_ID` (Haiku), ignoring the agent's `model` class attribute.  `NVIDIAModelClient` always calls its configured `_model_id` (Ultra or Lightning), also ignoring the agent's string.  Agents carry Claude model strings only as documentation reminders; they are not operative at runtime.

Each call resolves through `MultiTierModelClient` — the table below shows which model actually handles the call assuming no tier failure.  If a tier fails, the next tier in the chain is used automatically.

| Agent | NVIDIA mode (Tier 1) | NVIDIA mode (Tier 2) | NVIDIA mode (Tier 3) |
|-------|---|---|---|
| Certification Advisor | Ultra | Lightning | Haiku |
| Skill Profiler | Ultra | Lightning | Haiku |
| Curriculum Planner | Ultra | Lightning | Haiku |
| Item-Writer | Ultra | Lightning | Haiku |
| Quiz Batch Generator | Ultra | Lightning | Haiku |
| Grader | Ultra | Lightning | Haiku |
| Domain Scorer | Ultra | Lightning | Haiku → mechanical fallback if all fail |
| Cert Skill Mapper | Ultra | Lightning | Haiku |
| Usage-Signal | Ultra | Lightning | Haiku |
| Correlation | Ultra | Lightning | Haiku |
| Nudge Composer | Ultra | Lightning | Haiku |
| Nudge Category Generator | Ultra | Lightning | Haiku |

In `APP_BRAIN_MODEL=ANTHROPIC` mode the order is: Haiku (Tier 1) → Ultra (Tier 2) → Lightning (Tier 3).

## Prompt Tuning for Nemotron

Nemotron 3 Ultra has different strengths than Claude. If you observe quality issues:

1. **Be more explicit in prompts**: Nemotron benefits from clearer instructions and fewer implicit assumptions.
2. **Add examples**: Few-shot examples in prompts often improve Nemotron output quality.
3. **Simplify complex reasoning**: Break multi-step reasoning into sequential agent calls if needed.
4. **Check structured output compliance**: Ensure JSON schemas are simple and well-defined.

### Per-Agent Prompt Adjustments

If needed, modify `backend/app/agents/prompts/<agent>.md`:

- **Certification Advisor**: Add explicit "think step by step" for matching logic
- **Grader**: Provide more detailed rubric examples for free-text grading
- **Correlation**: Strengthen "correlation ≠ causation" framing with examples
- **Nudge Composer**: Add more tone examples (encouraging vs. demanding)

## Testing with Both Providers

### Run Tests with Anthropic (default)

```bash
cd backend
APP_BRAIN_MODEL=ANTHROPIC py -m pytest tests/scenarios/ -v
```

### Run Tests with NVIDIA

```bash
cd backend
APP_BRAIN_MODEL=NVIDIA NVIDIA_API_KEY=your-key py -m pytest tests/scenarios/ -v
```

### Dual-Provider Regression in CI

Tests are parametrized for both providers. Run:

```bash
# Both providers
cd backend
APP_BRAIN_MODEL=ANTHROPIC py -m pytest tests/scenarios/ -v -m "not integration"
APP_BRAIN_MODEL=NVIDIA NVIDIA_API_KEY=your-key py -m pytest tests/scenarios/ -v -m "not integration"
```

## Troubleshooting

### "NVIDIA_API_KEY is required when APP_BRAIN_MODEL=NVIDIA"

Set the `NVIDIA_API_KEY` environment variable or add it to `.env`.

### "Invalid APP_BRAIN_MODEL value"

Valid values are exactly `ANTHROPIC` or `NVIDIA` (case-insensitive).

### Structured Output Validation Errors

If Nemotron returns malformed JSON that fails Pydantic validation:
1. Check the prompt for ambiguous instructions
2. Simplify the output schema (fewer nested objects)
3. Add explicit format requirements in the prompt

### MCP Warning Logs

When using NVIDIA, you'll see warnings like:
```
WARNING: Skill Profiler running with NVIDIA provider — skipping mcp-learning-portal data
```

This is expected. The agent will use only `skill_profile_events` data.

### Higher Nightly Pulse Costs with NVIDIA

Expected — NVIDIA doesn't support Message Batches API. The workflow runs synchronously instead.

## Architecture Details

See `docs/architecture.md` §Multi-Model Provider Support for:
- Abstraction layer design (`ModelClient` protocol)
- Implementation details (`AnthropicModelClient`, `NVIDIAModelClient`)
- Factory function (`create_model_client`)
- MCP compatibility implementation

## Code Changes for Provider-Agnostic Development

When adding new agents or modifying existing ones:

1. **Never import `anthropic` or `openai` directly in agents**
2. **Accept `ModelClient` in `__init__`** (already the default via `Agent` base class)
3. **Use `create_model_client()` in workflows/routes** for automatic provider selection
4. **Override `_transient_errors` in agent subclasses** if using provider-specific error types
5. **Keep prompts provider-agnostic** — single `.md` file per agent

## Verification Checklist

After switching providers or deploying to Render, verify:

- [ ] All scenario tests pass (`py -m pytest tests/scenarios/`)
- [ ] `agent_runs.model_used` shows `claude-haiku-4-5-20251001` for Anthropic calls (never `claude-sonnet-5` or `claude-opus-5`)
- [ ] `agent_runs.model_used` shows Ultra model ID for healthy NVIDIA-primary calls
- [ ] When Ultra fails and Lightning succeeds, `agent_runs.model_used` shows the Lightning model ID
- [ ] When both NVIDIA tiers fail and Haiku answers, `agent_runs.model_used` shows Haiku
- [ ] Server logs show `WARNING: Primary provider failed` lines before any Haiku fallback entry
- [ ] After 5 consecutive NVIDIA-both-fail calls, logs show circuit-breaker WARNING and subsequent calls skip to Haiku immediately (no 10s + 20s wait)
- [ ] Circuit breaker resets after 2 minutes — logs show reset INFO and Ultra is tried again
- [ ] Profile lock completes in ≤ 50 s in the worst case (all three tiers fail sequentially)
- [ ] Profiles with degraded scoring show amber badge on radar and domain chart
- [ ] All-providers-unavailable from grader/quiz-batch → HTTP 503 with `retry_after_seconds` in body
- [ ] Skill Profiler runs without MCP data (check logs for warning)
- [ ] Usage-Signal runs with empty signals (check logs for warning)
- [ ] Token counts and latency are tracked correctly for whichever tier responded

## Rolling Back

To revert to Anthropic:

```bash
APP_BRAIN_MODEL=ANTHROPIC
ANTHROPIC_API_KEY=your-key
# Remove or comment out NVIDIA_* variables
```

No database migrations or code changes required — the switch is purely configuration-based.