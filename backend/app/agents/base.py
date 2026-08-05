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

import time
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Generic, Protocol, TypeVar, runtime_checkable

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
    """Minimal shape of what client.messages.parse() returns."""

    parsed: TOutput

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
        name        — matches the prompt filename (prompts/<name>.md)
        model       — Claude model ID to use (see docs/architecture.md)
        output_model — Pydantic model that defines the Structured Output schema

    And must implement:
        _build_messages(input) → list[dict]   (converts input → Claude messages)

    Optionally override:
        max_tokens  — default 4096
    """

    name: str
    model: str
    output_model: type[TOutput]
    max_tokens: int = 4096

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
        """Execute the agent: call Claude, persist agent_runs, return typed output."""
        started_at = datetime.now(UTC)
        start_ns = time.perf_counter_ns()
        run_id = str(uuid.uuid4())

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
                error_message=str(exc),
                started_at=started_at,
            )
            raise

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

        # Validate the parsed output against our schema.
        # With the real SDK this is a no-op (already validated); with stubs it
        # catches bad test fixtures early rather than silently returning garbage.
        if not isinstance(response.parsed, self.output_model):
            try:
                validated = self.output_model.model_validate(
                    response.parsed
                    if isinstance(response.parsed, dict)
                    else response.parsed.model_dump()
                )
            except pydantic.ValidationError:
                raise
        else:
            validated = response.parsed

        # Extract token counts (may be None on stubs).
        try:
            tokens_in: int | None = response.usage.input_tokens
            tokens_out: int | None = response.usage.output_tokens
        except AttributeError:
            tokens_in = tokens_out = None

        return validated, tokens_in, tokens_out

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
        """Write an agent_runs row. Skipped if no db_session was provided."""
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
        await self._db.flush()  # write within the caller's transaction; they commit.
