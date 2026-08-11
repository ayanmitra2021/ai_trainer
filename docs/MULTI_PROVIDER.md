# Multi-Provider Migration Guide

This guide explains how to switch between Anthropic Claude and NVIDIA Nemotron 3 Ultra as the LLM provider for Mastery Pulse.

## Quick Start

### Switching to NVIDIA Nemotron

```bash
# In your .env file:
APP_BRAIN_MODEL=NVIDIA
NVIDIA_API_KEY=nvapi-your-key-here
# NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1  # optional, defaults to this
# NVIDIA_MODEL_ID=nvidia/llama-3.1-nemotron-ultra-253b-v1  # optional, defaults to this
```

### Switching to Anthropic (default)

```bash
# In your .env file:
APP_BRAIN_MODEL=ANTHROPIC
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

## Configuration Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_BRAIN_MODEL` | Yes | `ANTHROPIC` | Provider selection: `ANTHROPIC` or `NVIDIA` |
| `ANTHROPIC_API_KEY` | When ANTHROPIC | - | Anthropic API key from console.anthropic.com |
| `NVIDIA_API_KEY` | When NVIDIA | - | NVIDIA API key from integrate.api.nvidia.com |
| `NVIDIA_BASE_URL` | No | `https://integrate.api.nvidia.com/v1` | NVIDIA API endpoint (OpenAI-compatible) |
| `NVIDIA_MODEL_ID` | No | `nvidia/llama-3.1-nemotron-ultra-253b-v1` | Model identifier |

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

| Agent | Anthropic Default | NVIDIA Default |
|-------|-------------------|----------------|
| Certification Advisor | `claude-sonnet-5` | `nvidia/llama-3.1-nemotron-ultra-253b-v1` |
| Skill Profiler | `claude-sonnet-5` | `nvidia/llama-3.1-nemotron-ultra-253b-v1` |
| Curriculum Planner | `claude-sonnet-5` | `nvidia/llama-3.1-nemotron-ultra-253b-v1` |
| Item-Writer | `claude-sonnet-5` (Opus 5 for hard items) | `nvidia/llama-3.1-nemotron-ultra-253b-v1` |
| Grader | `claude-opus-5` / `claude-haiku-4.5` | `nvidia/llama-3.1-nemotron-ultra-253b-v1` |
| Usage-Signal | `claude-haiku-4.5` | `nvidia/llama-3.1-nemotron-ultra-253b-v1` |
| Correlation | `claude-opus-5` | `nvidia/llama-3.1-nemotron-ultra-253b-v1` |
| Nudge Composer | `claude-sonnet-5` | `nvidia/llama-3.1-nemotron-ultra-253b-v1` |
| Rollup Reporter | `claude-sonnet-5` | `nvidia/llama-3.1-nemotron-ultra-253b-v1` |
| Nudge Category Generator | `claude-sonnet-5` | `nvidia/llama-3.1-nemotron-ultra-253b-v1` |

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

After switching providers, verify:

- [ ] All scenario tests pass (`py -m pytest tests/scenarios/`)
- [ ] Skill Profiler runs without MCP data (check logs for warning)
- [ ] Usage-Signal runs with empty signals (check logs for warning)
- [ ] Nightly Pulse completes (synchronously with NVIDIA)
- [ ] Agent runs record correct `model_used` in `agent_runs` table
- [ ] Token counts and latency are tracked for both providers
- [ ] Observability dashboard shows correct model names

## Rolling Back

To revert to Anthropic:

```bash
APP_BRAIN_MODEL=ANTHROPIC
ANTHROPIC_API_KEY=your-key
# Remove or comment out NVIDIA_* variables
```

No database migrations or code changes required — the switch is purely configuration-based.