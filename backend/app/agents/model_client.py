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
from datetime import UTC, datetime
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
    """Wrapper around anthropic.AsyncAnthropic.messages for Structured Outputs."""

    def __init__(self, client: anthropic.AsyncAnthropic) -> None:
        self._client = client

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
        return await self._client.messages.parse(
            model=model,
            system=system,
            messages=messages,
            max_tokens=max_tokens,
            output_format=output_format,
            **kwargs,
        )


class AnthropicModelClient(BaseModelClient, ModelClient):
    """Anthropic Claude client implementing the ModelClient protocol."""

    _transient_errors = (
        anthropic.RateLimitError,
        anthropic.APITimeoutError,
        anthropic.APIConnectionError,
        anthropic.InternalServerError,
    )

    def __init__(self, api_key: str) -> None:
        super().__init__()
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self.messages = AnthropicMessagesClient(self._client)

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
        return await self._retry_call(
            self.messages.parse,
            model=model,
            system=system,
            messages=messages,
            max_tokens=max_tokens,
            output_format=output_format,
            **kwargs,
        )


# ── NVIDIA (OpenAI-compatible) implementation ────────────────────────────────


def _extract_json_from_content(content: str) -> str:
    """Strip optional markdown code-block fences from an LLM response.

    NVIDIA Nemotron sometimes wraps its JSON output in ```json ... ``` even
    when instructed not to. This helper extracts the raw JSON string so that
    json.loads() can parse it cleanly.
    """
    content = content.strip()
    if content.startswith("```"):
        # Drop the opening fence line (e.g. "```json\n" or "```\n")
        newline = content.find("\n")
        if newline != -1:
            content = content[newline + 1:]
        # Drop the closing fence
        if content.rstrip().endswith("```"):
            content = content.rstrip()[:-3].rstrip()
    return content.strip()


class NVIDIAMessagesClient(MessagesClient):
    """Wrapper around openai.AsyncOpenAI for NVIDIA Nemotron Structured Outputs.

    NVIDIA's NIM API is OpenAI-compatible but doesn't support
    ``beta.chat.completions.parse`` or ``response_format`` JSON-schema mode.
    Instead we embed the JSON schema in the system prompt and parse the response
    manually.

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

        # Build messages with system prompt + JSON schema instruction
        schema_instruction = (
            f"\n\nYou must respond with a valid JSON object that matches this schema "
            f"exactly. Output only raw JSON — no markdown fences, no explanation:\n"
            f"{json.dumps(schema, indent=2)}"
        )

        openai_messages = [
            {"role": "system", "content": system + schema_instruction}
        ] + messages

        # Use standard chat completions with the configured NVIDIA model ID.
        # Agents pass a Claude model string; we discard it and use self._model_id.
        response = await self._client.chat.completions.create(
            model=self._model_id,
            messages=openai_messages,
            max_tokens=max_tokens,
            **kwargs,
        )

        # Parse and validate the JSON response
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("Empty response from NVIDIA API")

        # Strip markdown fences that the model may add despite instructions
        content = _extract_json_from_content(content)

        try:
            parsed_data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Failed to parse JSON from NVIDIA response: {e}\n"
                f"Raw content (first 500 chars): {content[:500]}"
            )

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
    """NVIDIA Nemotron client implementing the ModelClient protocol (OpenAI-compatible)."""

    _transient_errors = (
        openai.RateLimitError,
        openai.APITimeoutError,
        openai.APIConnectionError,
        openai.InternalServerError,
    )

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        model_id: str = "nvidia/llama-3.1-nemotron-ultra-253b-v1",
    ) -> None:
        super().__init__()
        self._model_id = model_id
        self._client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
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


# ── Factory function ──────────────────────────────────────────────────────────


def create_model_client() -> ModelClient:
    """Create the appropriate model client based on APP_BRAIN_MODEL setting.

    Returns:
        ModelClient: Either AnthropicModelClient or NVIDIAModelClient

    Raises:
        ValueError: If APP_BRAIN_MODEL is invalid or required API key is missing.
    """
    # Import get_settings here to ensure we get the latest cached settings
    from app.config import get_settings
    current_settings = get_settings()
    
    provider = current_settings.app_brain_model.upper()

    if provider == "ANTHROPIC":
        if not current_settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when APP_BRAIN_MODEL=ANTHROPIC")
        return AnthropicModelClient(api_key=current_settings.anthropic_api_key)

    elif provider == "NVIDIA":
        if not current_settings.nvidia_api_key:
            raise ValueError("NVIDIA_API_KEY is required when APP_BRAIN_MODEL=NVIDIA")
        if not current_settings.nvidia_api_key.startswith("nvapi-"):
            raise ValueError(
                f"NVIDIA_API_KEY looks malformed: it must start with 'nvapi-' but starts with "
                f"{current_settings.nvidia_api_key[:8]!r}. Check your .env for a stray character."
            )
        return NVIDIAModelClient(
            api_key=current_settings.nvidia_api_key,
            base_url=current_settings.nvidia_base_url,
            model_id=current_settings.nvidia_model_id,
        )

    else:
        raise ValueError(
            f"Invalid APP_BRAIN_MODEL: '{current_settings.app_brain_model}'. "
            f"Valid values: 'ANTHROPIC', 'NVIDIA'"
        )


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