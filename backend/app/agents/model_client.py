"""Model Client Abstraction Layer — Phase 8.

Provides a unified interface for Anthropic and NVIDIA (OpenAI-compatible) LLM providers.
Both implementations support Structured Outputs, token counting, latency measurement,
and consistent error handling.
"""

from __future__ import annotations

import asyncio
import json
import time
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Generic, Protocol, TypeVar, runtime_checkable

import anthropic
import openai
from pydantic import BaseModel

from app.config import settings

# ── Type parameters ───────────────────────────────────────────────────────────

TOutput = TypeVar("TOutput", bound=BaseModel)

# ── Protocol definitions ──────────────────────────────────────────────────────


class ParsedResponse(Protocol[TOutput]):
    """Minimal shape of what client.messages.parse() returns.

    The real Anthropic SDK (>=0.100) returns a ParsedMessage where the parsed
    output lives on each content block as `block.parsed_output`. Test stubs
    use a simpler structure with a top-level `parsed` attribute. _extract_parsed
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
        output_format: type[BaseModel],
        **kwargs: Any,
    ) -> Any:  # ParsedResponse
        ...


@runtime_checkable
class ModelClient(Protocol):
    """Top-level model client — real Anthropic, NVIDIA (OpenAI), or a stub."""

    messages: MessagesClient

    async def parse(
        self,
        *,
        model: str,
        system: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        output_format: type[BaseModel],
        **kwargs: Any,
    ) -> Any:
        ...


# ── Base implementation ───────────────────────────────────────────────────────


class BaseModelClient(ABC, Generic[TOutput]):
    """Abstract base for model clients with shared retry/error logic."""

    def __init__(self) -> None:
        pass

    @property
    @abstractmethod
    def _transient_errors(self) -> tuple[type[BaseException], ...]:
        """Exception types that represent transient infrastructure failures."""
        ...

    async def _retry_call(self, call_fn, *args, max_retries: int = 3, retry_base_delay_s: float = 1.0, **kwargs) -> Any:
        """Execute call with exponential backoff retry on transient errors."""
        last_exc: BaseException | None = None

        for attempt in range(max_retries + 1):
            try:
                return await call_fn(*args, **kwargs)

            except Exception as exc:
                last_exc = exc
                is_transient = isinstance(exc, self._transient_errors)
                if is_transient and attempt < max_retries:
                    delay = retry_base_delay_s * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue
                break

        assert last_exc is not None
        raise last_exc


# ── Anthropic implementation ─────────────────────────────────────────────────


class AnthropicMessagesClient(MessagesClient):
    """Wrapper around anthropic.AsyncAnthropic.messages for Structured Outputs.

    Always calls ``self._model_id`` — the caller's ``model`` argument is
    intentionally ignored.  Agents carry Claude model strings as documentation
    reminders; the actual model is pinned via ``AnthropicModelClient(model_id=…)``.
    """

    def __init__(self, client: anthropic.AsyncAnthropic, model_id: str) -> None:
        self._client = client
        self._model_id = model_id  # always use this; ignore whatever agents pass

    async def parse(
        self,
        *,
        model: str,  # noqa: ARG002 — agent passes a Claude model string; we override it
        system: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        output_format: type[BaseModel],
        **kwargs: Any,
    ) -> Any:
        return await self._client.messages.parse(
            model=self._model_id,
            system=system,
            messages=messages,
            max_tokens=max_tokens,
            output_format=output_format,
            **kwargs,
        )


class AnthropicModelClient(BaseModelClient, ModelClient):
    """Anthropic Claude client implementing the ModelClient protocol.

    All calls use ``model_id`` (default ``claude-haiku-4-5-20251001``).
    Individual agent ``model`` class attributes are ignored — the model is
    pinned at client construction time for cost control.
    """

    _transient_errors = (
        anthropic.RateLimitError,
        anthropic.APITimeoutError,
        anthropic.APIConnectionError,
        anthropic.InternalServerError,
    )

    def __init__(
        self,
        api_key: str,
        model_id: str = "claude-haiku-4-5-20251001",
        request_timeout: float = 30.0,
    ) -> None:
        super().__init__()
        self._model_id = model_id
        self._client = anthropic.AsyncAnthropic(
            api_key=api_key,
            timeout=request_timeout,
        )
        self.messages = AnthropicMessagesClient(self._client, model_id=model_id)

    async def parse(
        self,
        *,
        model: str,  # noqa: ARG002 — agent's Claude model string; overridden internally
        system: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        output_format: type[BaseModel],
        **kwargs: Any,
    ) -> Any:
        # Pass self._model_id rather than the agent's model string.
        return await self._retry_call(
            self.messages.parse,
            model=self._model_id,
            system=system,
            messages=messages,
            max_tokens=max_tokens,
            output_format=output_format,
            **kwargs,
        )


# ── NVIDIA (OpenAI-compatible) implementation ────────────────────────────────


def _strip_thinking_tags(content: str) -> str:
    """Remove <think>…</think> blocks that Nemotron Ultra and similar reasoning
    models emit before their actual answer.

    These blocks contain the model's chain-of-thought and should never be
    parsed as part of the JSON output.  We strip all occurrences (there is
    usually only one) before handing the content to _extract_json_from_content.
    """
    import re
    # Remove <think>…</think> blocks (non-greedy, DOTALL so newlines match)
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
    return content.strip()


def _normalize_json_keys(data: object) -> object:
    """Recursively strip trailing ': ' / ':' from JSON keys.

    Nemotron Ultra sometimes emits keys like ``"item_type: ": "mcq"`` —
    echoing a field-description colon into the key name.  This normaliser
    converts ``'item_type: '`` → ``'item_type'`` without touching key
    bodies that legitimately contain colons in the middle (e.g. URL keys).

    Uses a regex so that only a *trailing* ``:<whitespace>`` sequence is
    removed, preventing rstrip(': ') from eating trailing characters such
    as the trailing 's' in ``'items: '`` → would wrongly become ``'item'``.
    """
    import re as _re
    if isinstance(data, dict):
        return {
            _re.sub(r":\s*$", "", k).strip(): _normalize_json_keys(v)
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [_normalize_json_keys(item) for item in data]
    return data


def _extract_json_from_content(content: str) -> str:
    """Extract a JSON object from an LLM response that may contain surrounding text.

    Handles these output patterns (in order):

    0. ``<think>…</think>`` reasoning blocks — stripped first by
       _strip_thinking_tags before this function is called.
    1. ````json ... ``` ` fences — strips the fences (some models add these
       despite being told not to).
    2. Pure JSON starting with ``{`` — returned as-is.
    3. Reasoning/prose followed by a JSON object — this is the characteristic
       output of thinking/reasoning models like NVIDIA Nemotron Ultra, which
       walk through their logic in plain text and then emit the JSON at the end.
       We find the last ``{...}`` block by scanning the string from the right.

    Any of these can also have a trailing ``` after the JSON; the fence-stripping
    in case 1 handles that too.
    """
    content = content.strip()

    # Pattern 1: markdown fences (```json … ``` or ``` … ```)
    if content.startswith("```"):
        newline = content.find("\n")
        if newline != -1:
            content = content[newline + 1:]
        if content.rstrip().endswith("```"):
            content = content.rstrip()[:-3].rstrip()
        return content.strip()

    # Pattern 2: pure JSON object
    if content.startswith("{"):
        return content

    # Pattern 3: reasoning text followed by a JSON object.
    # Find the rightmost `}` then walk left to find its matching `{`.
    last_close = content.rfind("}")
    if last_close != -1:
        depth = 0
        for i in range(last_close, -1, -1):
            if content[i] == "}":
                depth += 1
            elif content[i] == "{":
                depth -= 1
                if depth == 0:
                    return content[i : last_close + 1]

    # No JSON object found — return as-is so json.loads() raises a clear error
    return content


class NVIDIAMessagesClient(MessagesClient):
    """Wrapper around openai.AsyncOpenAI for NVIDIA Nemotron Structured Outputs.

    NVIDIA's NIM API is OpenAI-compatible.  We use ``response_format`` JSON-object
    mode to force valid JSON output, and embed the Pydantic schema in the system
    prompt so the model knows which fields to populate.

    Nemotron Ultra emits ``<think>…</think>`` reasoning blocks before the JSON
    answer; we strip those before parsing so they never contaminate the output.

    The ``model`` argument received from agent code is intentionally IGNORED —
    agents carry hardcoded Claude model strings; the NVIDIA client must always
    use the model ID it was initialised with (``model_id``).
    """

    def __init__(self, client: openai.AsyncOpenAI, model_id: str) -> None:
        self._client = client
        self._model_id = model_id  # always use this; ignore whatever agents pass

    async def parse(
        self,
        *,
        model: str,  # noqa: ARG002 — caller passes a Claude model ID; we override it
        system: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        output_format: type[BaseModel],
        **kwargs: Any,
    ) -> Any:
        # Convert Pydantic model to JSON schema for the prompt
        schema = output_format.model_json_schema()

        # Embed the schema as an explicit instruction.  response_format below
        # guarantees valid JSON; the schema text tells the model which fields
        # to fill and what types they must have.
        schema_instruction = (
            f"\n\nRespond with a single JSON object — no markdown fences, no prose "
            f"outside the JSON, no explanation.  The object must contain exactly "
            f"these fields (fill every required field; use null for optional ones "
            f"you cannot determine):\n"
            f"{json.dumps(schema, indent=2)}"
        )

        openai_messages = [
            {"role": "system", "content": system + schema_instruction}
        ] + messages

        # Do NOT pass response_format — the NVIDIA NIM endpoint changed its
        # structured-output validation and now rejects {"type": "json_object"}
        # with a 400 error.  The system prompt already embeds the full JSON
        # schema and instructs the model to return only a JSON object.
        # _strip_thinking_tags + _extract_json_from_content reliably parse the
        # output whether or not the model prefixes prose or a <think> block.
        response = await self._client.chat.completions.create(
            model=self._model_id,
            messages=openai_messages,
            max_tokens=max_tokens,
            **kwargs,
        )

        # Parse and validate the JSON response.
        # Strip <think>…</think> reasoning blocks that Nemotron Ultra emits
        # before the answer, then extract the JSON object.
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("Empty response from NVIDIA API")

        content = _strip_thinking_tags(content)
        content = _extract_json_from_content(content)

        try:
            parsed_data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Failed to parse JSON from NVIDIA response: {e}\n"
                f"Raw content (first 500 chars): {content[:500]}"
            )

        # Nemotron sometimes emits keys with trailing ': ' (e.g. "item_type: ").
        # Normalise before validation so Pydantic sees the correct field names.
        parsed_data = _normalize_json_keys(parsed_data)

        # Validate against the Pydantic model
        validated = output_format.model_validate(parsed_data)

        # Create a response object that mimics the Anthropic SDK parse() shape
        # so _extract_parsed() and token-counting in base.py work unchanged.
        class _FakeChoice:
            def __init__(self, message_content: BaseModel):
                self.message = _FakeMessage(message_content)

        class _FakeMessage:
            def __init__(self, parsed: BaseModel):
                self.parsed = parsed
                self.content = parsed.model_dump_json()

        class _FakeUsage:
            # NVIDIA/OpenAI uses prompt_tokens / completion_tokens;
            # base.py expects input_tokens / output_tokens (Anthropic naming).
            def __init__(self, usage: Any):
                self.input_tokens = getattr(usage, "prompt_tokens", 0) or 0
                self.output_tokens = getattr(usage, "completion_tokens", 0) or 0

        class _FakeResponse:
            def __init__(self, choices: list, usage: Any):
                self.choices = choices
                self.usage = _FakeUsage(usage)

        return _FakeResponse(
            choices=[_FakeChoice(validated)],
            usage=response.usage,
        )


class NVIDIAModelClient(BaseModelClient, ModelClient):
    """NVIDIA Nemotron client implementing the ModelClient protocol (OpenAI-compatible).

    When used inside FallbackModelClient, retries are disabled (empty tuple) —
    with a fallback chain, retrying a slow NVIDIA call wastes the time that the
    Haiku fallback could already be using.  One attempt per tier; if it fails,
    the fallback client takes over.
    """

    # Phase 14.2: no retries — FallbackModelClient handles failure routing.
    _transient_errors: tuple[type[BaseException], ...] = ()

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        model_id: str = "nvidia/llama-3.1-nemotron-ultra-253b-v1",
        request_timeout: float = 45.0,
    ) -> None:
        super().__init__()
        self._model_id = model_id
        # Explicit timeout so a hung NVIDIA endpoint doesn't block for the
        # OpenAI SDK default of 600 s. 45 s gives the API enough time for a
        # slow-but-healthy response while failing fast on a degraded endpoint.
        self._client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=request_timeout,
        )
        self.messages = NVIDIAMessagesClient(self._client, model_id=model_id)

    async def parse(
        self,
        *,
        model: str,  # noqa: ARG002 — Claude model string from agents; overridden internally
        system: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        output_format: type[BaseModel],
        **kwargs: Any,
    ) -> Any:
        # Pass self._model_id rather than the agent's Claude model string.
        return await self._retry_call(
            self.messages.parse,
            model=self._model_id,
            system=system,
            messages=messages,
            max_tokens=max_tokens,
            output_format=output_format,
            **kwargs,
        )


# ── Provider resilience (Phase 14 + 15) ───────────────────────────────────────

import logging as _logging

_fallback_log = _logging.getLogger(__name__)
_breaker_log = _logging.getLogger(__name__ + ".circuit_breaker")


class ProviderUnavailableError(RuntimeError):
    """Raised by FallbackModelClient (Phase 14 two-tier chain).

    Kept for backward compatibility — Phase 15 code raises AllProvidersUnavailableError.
    Carry both the primary and (optional) fallback errors so callers can
    log or surface the full failure story.
    """

    def __init__(
        self,
        primary_error: BaseException,
        fallback_error: BaseException | None = None,
    ) -> None:
        self.primary_error = primary_error
        self.fallback_error = fallback_error
        super().__init__(
            f"All providers unavailable. "
            f"Primary: {primary_error!r}. "
            f"Fallback: {fallback_error!r}"
        )


class AllProvidersUnavailableError(RuntimeError):
    """Raised when every tier of the MultiTierModelClient chain has been exhausted.

    Phase 15 replacement for ProviderUnavailableError — carries the full list of
    per-tier exceptions so callers can log or surface the complete failure story.
    The global 503 handler in main.py catches this and returns Retry-After: 120.
    """

    def __init__(self, errors: list[Exception]) -> None:
        self.errors = errors
        msgs = "; ".join(repr(e) for e in errors)
        super().__init__(f"All providers unavailable. Tier errors: {msgs}")


class FallbackModelClient:
    """Two-tier provider fallback chain (Phase 14 — kept for backward compat).

    Phase 15 replaces this with MultiTierModelClient for new deployments.
    FallbackModelClient is still imported by Phase 14 scenario tests, so it
    must remain here unchanged.

    Chain: primary → fallback → ProviderUnavailableError.
    """

    _last_model_used: str | None = None

    def __init__(
        self,
        primary: ModelClient,
        fallback: ModelClient | None = None,
        primary_timeout: float = 45.0,
        fallback_timeout: float = 30.0,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._primary_timeout = primary_timeout
        self._fallback_timeout = fallback_timeout
        self._last_model_used = None

    async def parse(
        self,
        *,
        model: str,
        system: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        output_format: type[BaseModel],
        **kwargs: Any,
    ) -> Any:
        primary_exc: BaseException | None = None

        try:
            result = await asyncio.wait_for(
                self._primary.parse(
                    model=model,
                    system=system,
                    messages=messages,
                    max_tokens=max_tokens,
                    output_format=output_format,
                    **kwargs,
                ),
                timeout=self._primary_timeout,
            )
            self._last_model_used = getattr(self._primary, "_model_id", model)
            return result
        except Exception as exc:
            primary_exc = exc
            _fallback_log.warning(
                "Primary provider failed (%s) — attempting fallback. Error: %s",
                getattr(self._primary, "_model_id", "primary"),
                exc,
            )

        if self._fallback is None:
            assert primary_exc is not None
            raise ProviderUnavailableError(primary_exc)

        try:
            result = await asyncio.wait_for(
                self._fallback.parse(
                    model=model,
                    system=system,
                    messages=messages,
                    max_tokens=max_tokens,
                    output_format=output_format,
                    **kwargs,
                ),
                timeout=self._fallback_timeout,
            )
            self._last_model_used = getattr(
                self._fallback, "_model_id", "haiku-fallback"
            )
            return result
        except Exception as fallback_exc:
            assert primary_exc is not None
            raise ProviderUnavailableError(primary_exc, fallback_exc)

    @property
    def messages(self) -> "FallbackModelClient":
        return self


# ── Phase 15: Circuit Breaker ─────────────────────────────────────────────────


class NvidiaCircuitBreaker:
    """In-memory circuit breaker for the NVIDIA provider estate.

    State machine
    -------------
    CLOSED (normal): every call tries the full NVIDIA→Haiku chain.
    OPEN (cooldown): NVIDIA tiers are skipped; Haiku is used directly.

    The breaker OPENS after ``threshold`` consecutive calls where BOTH NVIDIA
    tiers fail on the same request. A partial failure (Ultra fails, Lightning
    succeeds) does NOT increment the counter — the NVIDIA estate is partially
    healthy.

    The breaker auto-RESETS when ``open_until`` is reached (checked lazily on
    each call to ``is_open``).

    Persistence: in-process memory only — a server restart resets the breaker.
    """

    def __init__(
        self,
        threshold: int = 5,
        cooldown_seconds: float = 120.0,
    ) -> None:
        self.threshold = threshold
        self.cooldown_seconds = cooldown_seconds
        self.consecutive_failures: int = 0
        self.open_until: datetime | None = None

    @property
    def is_open(self) -> bool:
        """True when the breaker is in cooldown (OPEN state).

        Lazily resets when cooldown expires — no background task needed.
        """
        if self.open_until is None:
            return False
        if datetime.now(UTC) >= self.open_until:
            _breaker_log.info("NVIDIA circuit breaker reset — resuming normal tier chain")
            self.open_until = None
            self.consecutive_failures = 0
            return False
        return True

    def record_nvidia_both_failed(self) -> None:
        """Record that BOTH NVIDIA tiers failed on the same call.

        Increments the consecutive-failure counter and trips the breaker when
        the threshold is reached.
        """
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.threshold and self.open_until is None:
            self.open_until = datetime.now(UTC) + timedelta(seconds=self.cooldown_seconds)
            _breaker_log.warning(
                "NVIDIA circuit breaker tripped after %d consecutive failures — "
                "%d-second cooldown until %s",
                self.consecutive_failures,
                int(self.cooldown_seconds),
                self.open_until.strftime("%H:%M:%S"),
            )

    def record_nvidia_partial_success(self) -> None:
        """Reset the counter when at least one NVIDIA tier succeeds."""
        if self.consecutive_failures > 0:
            self.consecutive_failures = 0


# ── Phase 15: Multi-Tier Client ───────────────────────────────────────────────


class MultiTierModelClient:
    """N-tier provider fallback chain (Phase 15 replacement for FallbackModelClient).

    Each tier is a ``(client, timeout_seconds)`` pair. Tiers are tried in order;
    on failure the next tier is attempted. If every tier fails,
    ``AllProvidersUnavailableError`` is raised.

    NVIDIA mode (``APP_BRAIN_MODEL=NVIDIA``):
      Tier 1 — NVIDIAModelClient(Ultra)       10 s timeout
      Tier 2 — NVIDIAModelClient(Lightning)   20 s timeout
      Tier 3 — AnthropicModelClient(Haiku)    20 s timeout

    ANTHROPIC mode (``APP_BRAIN_MODEL=ANTHROPIC``):
      Tier 1 — AnthropicModelClient(Haiku)    10 s timeout
      Tier 2 — NVIDIAModelClient(Ultra)       20 s timeout
      Tier 3 — NVIDIAModelClient(Lightning)   20 s timeout
      (no circuit breaker — NVIDIA is already a fallback in this mode)

    ``_last_model_used`` is updated after each successful call so
    ``Agent.effective_model`` reports the tier that actually responded.
    The ``_primary`` property gives base.py a best-guess before the first call.
    """

    _last_model_used: str | None = None

    def __init__(
        self,
        tiers: list[tuple[Any, float]],
        circuit_breaker: "NvidiaCircuitBreaker | None" = None,
        nvidia_tier_count: int = 2,
    ) -> None:
        if not tiers:
            raise ValueError("MultiTierModelClient requires at least one tier")
        self._tiers = tiers
        self._circuit_breaker = circuit_breaker
        self._nvidia_tier_count = nvidia_tier_count
        self._last_model_used = None

    @property
    def _primary(self) -> Any:
        """First tier's client — used by Agent.effective_model before first call."""
        return self._tiers[0][0] if self._tiers else None

    @property
    def messages(self) -> "MultiTierModelClient":
        """No-op messages attr so callers that do client.messages.parse() still work."""
        return self

    async def parse(
        self,
        *,
        model: str,
        system: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        output_format: type[BaseModel],
        **kwargs: Any,
    ) -> Any:
        errors: list[Exception] = []

        # Determine start tier (skip NVIDIA tiers when circuit breaker is open)
        start_tier = 0
        if self._circuit_breaker is not None and self._circuit_breaker.is_open:
            _breaker_log.info(
                "NVIDIA circuit breaker open — routing directly to Haiku (resets at %s)",
                self._circuit_breaker.open_until.strftime("%H:%M:%S")
                if self._circuit_breaker.open_until else "N/A",
            )
            start_tier = self._nvidia_tier_count

        nvidia_failures = 0  # count of NVIDIA-tier failures this call

        for i, (client, timeout) in enumerate(self._tiers):
            if i < start_tier:
                continue

            client_model_id = getattr(client, "_model_id", f"tier-{i}")
            is_nvidia_tier = (
                self._circuit_breaker is not None and i < self._nvidia_tier_count
            )

            try:
                result = await asyncio.wait_for(
                    client.parse(
                        model=model,
                        system=system,
                        messages=messages,
                        max_tokens=max_tokens,
                        output_format=output_format,
                        **kwargs,
                    ),
                    timeout=timeout,
                )
                self._last_model_used = client_model_id
                if is_nvidia_tier:
                    self._circuit_breaker.record_nvidia_partial_success()  # type: ignore[union-attr]
                return result

            except Exception as exc:
                errors.append(exc)
                _fallback_log.warning(
                    "Primary provider failed (%s) — trying next tier. Error: %s",
                    client_model_id,
                    exc,
                )
                if is_nvidia_tier:
                    nvidia_failures += 1
                    # As soon as both NVIDIA tiers have failed, update the circuit
                    # breaker — even if a subsequent Haiku tier ultimately succeeds.
                    # This must happen inside the loop (not at the end) so the
                    # failure counter increments on every call where both NVIDIA
                    # tiers fail, not only when the entire chain is exhausted.
                    if nvidia_failures >= self._nvidia_tier_count and start_tier == 0:
                        self._circuit_breaker.record_nvidia_both_failed()  # type: ignore[union-attr]

        raise AllProvidersUnavailableError(errors)


# ── Module-level NVIDIA circuit breaker singleton ─────────────────────────────

# Created lazily on first NVIDIA-mode create_model_client() call.
# Lives for the process lifetime — a restart intentionally resets state.
_nvidia_circuit_breaker: "NvidiaCircuitBreaker | None" = None


# ── Factory function ──────────────────────────────────────────────────────────


def create_model_client() -> ModelClient:
    """Create the appropriate model client based on APP_BRAIN_MODEL setting.

    Phase 15 behaviour
    ------------------
    All modes return a ``MultiTierModelClient`` (three-tier chain).

    NVIDIA mode (APP_BRAIN_MODEL=NVIDIA):
      Tier 1 — Ultra       NVIDIA_TIER1_TIMEOUT_SECS  (default 10 s)
      Tier 2 — Lightning   NVIDIA_TIER2_TIMEOUT_SECS  (default 20 s)
      Tier 3 — Haiku       ANTHROPIC_TIER_TIMEOUT_SECS (default 20 s)
      circuit breaker active (trips after NVIDIA_CIRCUIT_BREAKER_THRESHOLD failures)

    ANTHROPIC mode (APP_BRAIN_MODEL=ANTHROPIC):
      Tier 1 — Haiku       NVIDIA_TIER1_TIMEOUT_SECS  (default 10 s)
      Tier 2 — Ultra       NVIDIA_TIER2_TIMEOUT_SECS  (default 20 s)
      Tier 3 — Lightning   ANTHROPIC_TIER_TIMEOUT_SECS (default 20 s)
      no circuit breaker (NVIDIA is already the fallback in this mode)

    ANTHROPIC mode with no NVIDIA key: single-tier Haiku-only chain.
    NVIDIA mode with no ANTHROPIC key: two-tier Ultra→Lightning chain.

    Raises:
        ValueError: If APP_BRAIN_MODEL is invalid or required API key is missing.
    """
    global _nvidia_circuit_breaker

    from app.config import get_settings
    s = get_settings()

    provider = s.app_brain_model.upper()

    if provider not in ("ANTHROPIC", "NVIDIA"):
        raise ValueError(
            f"Invalid APP_BRAIN_MODEL: '{s.app_brain_model}'. "
            f"Valid values: 'ANTHROPIC', 'NVIDIA'"
        )

    # ── Build individual tier clients ────────────────────────────────────
    haiku_client: AnthropicModelClient | None = None
    if s.anthropic_api_key:
        haiku_client = AnthropicModelClient(
            api_key=s.anthropic_api_key,
            model_id=s.app_anthropic_model_id,
            request_timeout=float(s.anthropic_tier_timeout_secs) + 5,
        )

    ultra_client: NVIDIAModelClient | None = None
    lightning_client: NVIDIAModelClient | None = None
    if s.nvidia_api_key:
        if not s.nvidia_api_key.startswith("nvapi-"):
            raise ValueError(
                f"NVIDIA_API_KEY looks malformed: must start with 'nvapi-' but starts with "
                f"{s.nvidia_api_key[:8]!r}. Check your .env for a stray character."
            )
        ultra_client = NVIDIAModelClient(
            api_key=s.nvidia_api_key,
            base_url=s.nvidia_base_url,
            model_id=s.nvidia_model_id_primary,
            request_timeout=float(s.nvidia_tier1_timeout_secs) + 5,
        )
        lightning_client = NVIDIAModelClient(
            api_key=s.nvidia_api_key,
            base_url=s.nvidia_base_url,
            model_id=s.nvidia_model_id_secondary,
            request_timeout=float(s.nvidia_tier2_timeout_secs) + 5,
        )

    # ── NVIDIA-primary mode ──────────────────────────────────────────────
    if provider == "NVIDIA":
        if not s.nvidia_api_key:
            raise ValueError("NVIDIA_API_KEY is required when APP_BRAIN_MODEL=NVIDIA")
        assert ultra_client is not None
        assert lightning_client is not None

        # Initialise the module-level circuit breaker (once per process)
        if _nvidia_circuit_breaker is None:
            _nvidia_circuit_breaker = NvidiaCircuitBreaker(
                threshold=s.nvidia_circuit_breaker_threshold,
                cooldown_seconds=float(s.nvidia_circuit_breaker_cooldown_secs),
            )

        tiers: list[tuple[Any, float]] = [
            (ultra_client, float(s.nvidia_tier1_timeout_secs)),
            (lightning_client, float(s.nvidia_tier2_timeout_secs)),
        ]
        if haiku_client is not None:
            tiers.append((haiku_client, float(s.anthropic_tier_timeout_secs)))

        return MultiTierModelClient(
            tiers=tiers,
            circuit_breaker=_nvidia_circuit_breaker,
            nvidia_tier_count=2,
        )

    # ── ANTHROPIC-primary mode ───────────────────────────────────────────
    # Haiku is required; NVIDIA models are optional fallbacks (no circuit breaker).
    if not s.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY is required when APP_BRAIN_MODEL=ANTHROPIC")
    assert haiku_client is not None

    anthro_tiers: list[tuple[Any, float]] = [
        (haiku_client, float(s.nvidia_tier1_timeout_secs)),
    ]
    if ultra_client is not None:
        anthro_tiers.append((ultra_client, float(s.nvidia_tier2_timeout_secs)))
    if lightning_client is not None:
        anthro_tiers.append((lightning_client, float(s.anthropic_tier_timeout_secs)))

    # ANTHROPIC mode: no circuit breaker (NVIDIA is already the fallback)
    return MultiTierModelClient(tiers=anthro_tiers, circuit_breaker=None)


# ── Helper for extracting parsed output ───────────────────────────────────────


def _extract_parsed(response: Any) -> Any:
    """Extract the parsed model instance from a parse() response.

    Handles two shapes:
    - Real Anthropic SDK >=0.100: ParsedMessage with content blocks where
      each text block carries a `parsed_output` attribute.
    - Real OpenAI SDK: ChatCompletion with `choices[0].message.parsed` attribute.
    - Test stub (_FakeParsedResponse): simple object with a `parsed` attr.
    """
    # Real Anthropic SDK path: iterate content blocks for parsed_output
    for block in getattr(response, "content", []):
        value = getattr(block, "parsed_output", None)
        if value is not None:
            return value

    # Real OpenAI SDK path: choices[0].message.parsed
    choices = getattr(response, "choices", None)
    if choices:
        message = getattr(choices[0], "message", None)
        if message:
            parsed = getattr(message, "parsed", None)
            if parsed is not None:
                return parsed

    # Stub / legacy fallback
    return getattr(response, "parsed", None)