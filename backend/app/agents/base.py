"""Base Agent class — the contract every agent in the system inherits.

Every agent is a typed, single-purpose unit:
  - One Pydantic input model (TInput)
  - One Pydantic output model (TOutput) — enforced via Structured Outputs
  - One agent_runs row written per call (observability + cost tracking)
  - One system prompt loaded from prompts/<agent_name>.md at runtime

Agents NEVER:
  - Import or call another agent directly (that's a workflow's job)
  - Decide whether to persist business-table rows (callers do that)
  - Parse JSON from a text response (Structured Outputs only)
  - Spawn MCP subprocesses unless explicitly configured with mcp_server_params

👤 Reviewed by Ayan before any other agent builds on this (see project_plan.md §0.4).
"""

from __future__ import annotations

import asyncio
import time
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Generic, Protocol, TypeVar, runtime_checkable

import anthropic
import pydantic
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AgentRun

# ── Type parameters ───────────────────────────────────────────────────────────

TInput = TypeVar("TInput", bound=BaseModel)
TOutput = TypeVar("TOutput", bound=BaseModel)

# ── Claude client protocol ────────────────────────────────────────────────────
# We depend on a narrow interface rather than the concrete anthropic.AsyncAnthropic
# class so that tests can substitute a stub without monkey-patching.


class ParsedResponse(Protocol[TOutput]):
    """Minimal shape of what client.messages.parse() returns.

    The real Anthropic SDK (>=0.100) returns a ParsedMessage where the parsed
    output lives on each content block as `block.parsed_output`.  Test stubs
    use a simpler structure with a top-level `parsed` attribute.  _extract_parsed
    handles both so neither path breaks.
    """

    class usage:
        input_tokens: int
        output_tokens: int


@runtime_checkable
class MessagesClient(Protocol):
    """Async messages client — real SDK or stub."""

    async def parse(
        self,
        *,
        model: str,
        system: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        output_format: type[TOutput],
        **kwargs: Any,
    ) -> Any:  # ParsedResponse[TOutput]
        ...


@runtime_checkable
class ClaudeClient(Protocol):
    """Top-level client — real anthropic.AsyncAnthropic or a stub."""

    messages: MessagesClient


# ── Agent base ────────────────────────────────────────────────────────────────

PROMPTS_DIR = Path(__file__).parent / "prompts"

# Sentinel used in tests to skip DB persistence (avoids needing a real DB for
# agents whose tests only care about the return value, not the audit row).
_NO_DB: AsyncSession | None = None


class Agent(ABC, Generic[TInput, TOutput]):
    """Generic base for all nine agents.

    Subclasses must set:
        name         — matches the prompt filename (prompts/<name>.md)
        model        — Claude model ID to use (see docs/architecture.md)
        output_model — Pydantic model that defines the Structured Output schema

    And must implement:
        _build_messages(input) → list[dict]   (converts input → Claude messages)

    Optionally override:
        max_tokens         — default 8192
        max_retries        — transient-error retries; default 3 (4 total attempts)
        retry_base_delay_s — first back-off delay in seconds; doubles each retry
        _transient_errors  — exception types that trigger a retry
    """

    name: str
    model: str
    output_model: type[TOutput]
    max_tokens: int = 8192
    max_retries: int = 3           # retries on transient errors (4 total attempts)
    retry_base_delay_s: float = 1.0  # first back-off; doubles each retry

    # Exception types that represent transient infrastructure failures and are
    # safe to retry. Validation, auth, and bad-request errors are NOT here —
    # they indicate a bug that won't resolve by itself.
    #
    # Subclasses may override this tuple. Tests typically substitute a simpler
    # exception type rather than constructing a real anthropic.RateLimitError.
    _transient_errors: tuple[type[BaseException], ...] = (
        anthropic.RateLimitError,
        anthropic.APITimeoutError,
        anthropic.APIConnectionError,
        anthropic.InternalServerError,
    )

    def __init__(
        self,
        client: ClaudeClient,
        db_session: AsyncSession | None = _NO_DB,
        workflow_run_id: str | None = None,
    ) -> None:
        self._client = client
        self._db = db_session
        self._workflow_run_id = workflow_run_id

    # ── Public API ────────────────────────────────────────────────────────

    async def run(self, input: TInput) -> TOutput:
        """Execute the agent: call Claude, persist agent_runs, return typed output.

        Retry policy
        ------------
        Transient errors (rate-limit, timeout, connection, 5xx) are retried up
        to self.max_retries times with exponential back-off:

            delay = retry_base_delay_s * 2^attempt

        All other errors (validation, auth, bad request) are not retried — they
        reflect a problem that won't resolve by itself.

        A single agent_runs row is written, reflecting the *final* outcome only,
        not each individual attempt. The latency_ms field covers the full wall
        time including any back-off sleep.

        Commit behaviour
        ----------------
        The agent commits its own audit row immediately on completion (success or
        final failure). This makes each agent self-contained: in a multi-agent
        workflow sharing one session, partial progress is visible in agent_runs
        even if a later agent fails. The trade-off is that the workflow no longer
        controls a single all-or-nothing transaction boundary for agent rows.
        """
        started_at = datetime.now(UTC)
        start_ns = time.perf_counter_ns()
        run_id = str(uuid.uuid4())
        last_exc: BaseException | None = None

        for attempt in range(self.max_retries + 1):
            try:
                output, tokens_in, tokens_out = await self._call_claude(input)
                latency_ms = (time.perf_counter_ns() - start_ns) // 1_000_000
                await self._persist_run(
                    run_id=run_id,
                    input=input,
                    output=output,
                    model_used=self.model,
                    tokens_input=tokens_in,
                    tokens_output=tokens_out,
                    latency_ms=latency_ms,
                    status="success",
                    error_message=None,
                    started_at=started_at,
                )
                return output

            except Exception as exc:
                last_exc = exc
                is_transient = isinstance(exc, self._transient_errors)
                if is_transient and attempt < self.max_retries:
                    delay = self.retry_base_delay_s * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue  # next attempt
                break  # non-transient error, or transient but retries exhausted

        # All retries exhausted, or a non-transient error broke out of the loop.
        assert last_exc is not None  # always set when we reach this point
        latency_ms = (time.perf_counter_ns() - start_ns) // 1_000_000
        await self._persist_run(
            run_id=run_id,
            input=input,
            output=None,
            model_used=self.model,
            tokens_input=None,
            tokens_output=None,
            latency_ms=latency_ms,
            status="error",
            error_message=str(last_exc),
            started_at=started_at,
        )
        raise last_exc  # type: ignore[misc]

    # ── Subclass hooks ────────────────────────────────────────────────────

    @abstractmethod
    def _build_messages(self, input: TInput) -> list[dict[str, Any]]:
        """Convert the typed input into the Claude messages list."""
        ...

    # ── Internal helpers ──────────────────────────────────────────────────

    def _load_prompt(self) -> str:
        """Load the agent's system prompt from prompts/<name>.md."""
        prompt_path = PROMPTS_DIR / f"{self.name}.md"
        if not prompt_path.exists():
            raise FileNotFoundError(
                f"Prompt file not found: {prompt_path}. "
                f"Create backend/app/agents/prompts/{self.name}.md before running this agent."
            )
        return prompt_path.read_text(encoding="utf-8").strip()

    async def _call_claude(
        self, input: TInput
    ) -> tuple[TOutput, int | None, int | None]:
        """Call the Claude API with Structured Outputs and return (output, tokens_in, tokens_out)."""
        system = self._load_prompt()
        messages = self._build_messages(input)

        response = await self._client.messages.parse(
            model=self.model,
            system=system,
            messages=messages,
            max_tokens=self.max_tokens,
            output_format=self.output_model,
        )

        raw = self._extract_parsed(response)
        if raw is None:
            raise ValueError(
                f"Agent '{self.name}': no parsed output found in response. "
                f"Content types: {[getattr(b, 'type', '?') for b in getattr(response, 'content', [])]}"
            )

        # Validate the parsed output against our schema.
        # With the real SDK this is a no-op (already validated); with stubs it
        # catches bad test fixtures early rather than silently returning garbage.
        if not isinstance(raw, self.output_model):
            try:
                validated = self.output_model.model_validate(
                    raw if isinstance(raw, dict) else raw.model_dump()
                )
            except pydantic.ValidationError:
                raise
        else:
            validated = raw

        # Extract token counts (may be None on stubs).
        try:
            tokens_in: int | None = response.usage.input_tokens
            tokens_out: int | None = response.usage.output_tokens
        except AttributeError:
            tokens_in = tokens_out = None

        return validated, tokens_in, tokens_out

    @staticmethod
    def _extract_parsed(response: Any) -> Any:
        """Extract the parsed model instance from a parse() response.

        Handles two shapes:
        - Real Anthropic SDK >=0.100: ParsedMessage with content blocks where
          each text block carries a `parsed_output` attribute.
        - Test stub (_FakeParsedResponse): simple object with a `parsed` attr.
        """
        # Real SDK path: iterate content blocks for parsed_output
        for block in getattr(response, "content", []):
            value = getattr(block, "parsed_output", None)
            if value is not None:
                return value
        # Stub / legacy fallback
        return getattr(response, "parsed", None)

    async def _persist_run(
        self,
        *,
        run_id: str,
        input: TInput | None,
        output: TOutput | None,
        model_used: str | None,
        tokens_input: int | None,
        tokens_output: int | None,
        latency_ms: int | None,
        status: str,
        error_message: str | None,
        started_at: datetime,
    ) -> None:
        """Write and commit an agent_runs row. Skipped if no db_session was provided.

        The agent commits its own row immediately (self-contained). In a workflow
        that shares one session across multiple agents, each commit is independent —
        so a later agent's failure won't roll back earlier agents' rows. This is
        intentional: crash-recovery observability over all-or-nothing atomicity.
        """
        if self._db is None:
            return

        completed_at = datetime.now(UTC)
        run = AgentRun(
            id=run_id,
            agent_name=self.name,
            workflow_run_id=self._workflow_run_id,
            input=input.model_dump(mode="json") if input is not None else None,
            output=output.model_dump(mode="json") if output is not None else None,
            model_used=model_used,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            latency_ms=latency_ms,
            status=status,
            error_message=error_message,
            started_at=started_at,
            completed_at=completed_at,
        )
        self._db.add(run)
        await self._db.commit()  # self-contained — agent owns its own audit row
