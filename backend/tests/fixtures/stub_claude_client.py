"""Stub Claude/NVIDIA client for agent scenario tests.

The stub is intentionally narrow — it only implements the surface the Agent
base class touches. Tests configure it with either a dict of response data
(which the stub validates against the expected output_format) or an exception
to raise, simulating API errors or validation failures.

Usage in conftest.py / tests:

    from tests.fixtures.stub_claude_client import StubClaudeClient, StubNVIDIAModelClient

    # Happy path — returns a valid response (Anthropic format)
    client = StubClaudeClient(response_data={"greeting": "hello", "score": 0.9})

    # Happy path — returns a valid response (OpenAI/NVIDIA format)
    client = StubNVIDIAModelClient(response_data={"greeting": "hello", "score": 0.9})

    # Error path — raises on every call
    client = StubClaudeClient(raise_exc=ValueError("network timeout"))

    # Malformed — data doesn't match the output schema; the Agent catches it
    client = StubClaudeClient(response_data={"wrong_field": 99})

    # Sequence — fail once with a transient error, then succeed
    client = StubClaudeClient(
        side_effects=[MyTransientError("rate limited")],
        response_data={"greeting": "hello", "score": 0.9},
    )

side_effects is consumed left-to-right, one item per call. Each item is either
an Exception (raised) or a dict (used as response_data for that call). Once
exhausted, subsequent calls fall back to raise_exc / response_data as usual.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from pydantic import BaseModel


class _FakeUsage:
    input_tokens: int = 100
    output_tokens: int = 50


class _FakeParsedResponse:
    """Returned by StubMessagesClient.parse() (Anthropic format)."""

    def __init__(self, parsed: BaseModel) -> None:
        self.parsed = parsed
        self.usage = _FakeUsage()


class _FakeChoice:
    """OpenAI/NVIDIA format choice with parsed message."""

    def __init__(self, parsed: BaseModel) -> None:
        self.message = _FakeMessage(parsed)


class _FakeMessage:
    """OpenAI/NVIDIA format message with parsed attribute."""

    def __init__(self, parsed: BaseModel) -> None:
        self.parsed = parsed


class _FakeNVIDIAResponse:
    """Returned by StubMessagesClient.parse() (OpenAI/NVIDIA format)."""

    def __init__(self, parsed: BaseModel) -> None:
        self.choices = [_FakeChoice(parsed)]
        self.usage = _FakeUsage()


class StubMessagesClient:
    """Implements the MessagesClient protocol — no real HTTP calls."""

    def __init__(
        self,
        response_data: dict[str, Any] | None = None,
        raise_exc: Exception | None = None,
        side_effects: list[dict[str, Any] | Exception] | None = None,
        response_format: str = "anthropic",  # "anthropic" or "openai"
    ) -> None:
        self._response_data = response_data or {}
        self._raise_exc = raise_exc
        # side_effects is consumed left-to-right, one item per parse() call.
        # Each item is either an Exception (raised) or a dict (response data).
        # When exhausted, falls back to raise_exc / response_data.
        self._side_effects: list[dict[str, Any] | Exception] = (
            list(side_effects) if side_effects else []
        )
        self._response_format = response_format
        # Track calls for assertions in tests
        self.call_count: int = 0
        self.last_call_kwargs: dict[str, Any] = {}

    async def parse(
        self,
        *,
        model: str,
        system: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        output_format: type[BaseModel],
        **kwargs: Any,
    ) -> _FakeParsedResponse | _FakeNVIDIAResponse:
        self.call_count += 1
        self.last_call_kwargs = dict(
            model=model,
            system=system,
            messages=messages,
            max_tokens=max_tokens,
            output_format=output_format,
            **kwargs,
        )

        # Consume the next side-effect if one is queued.
        if self._side_effects:
            effect = self._side_effects.pop(0)
            if isinstance(effect, Exception):
                raise effect
            parsed = output_format.model_validate(effect)
            return self._make_response(parsed)

        # Fall back to the configured default.
        if self._raise_exc is not None:
            raise self._raise_exc

        # Attempt to parse the raw dict into the expected output format.
        # If this raises ValidationError, the Agent base class will catch it
        # and record status='error' in agent_runs.
        parsed = output_format.model_validate(self._response_data)
        return self._make_response(parsed)

    def _make_response(self, parsed: BaseModel) -> _FakeParsedResponse | _FakeNVIDIAResponse:
        """Create response in the configured format."""
        if self._response_format == "openai":
            return _FakeNVIDIAResponse(parsed)
        return _FakeParsedResponse(parsed)


class StubClaudeClient:
    """Drop-in replacement for anthropic.AsyncAnthropic in tests (Anthropic format)."""

    def __init__(
        self,
        response_data: dict[str, Any] | None = None,
        raise_exc: Exception | None = None,
        side_effects: list[dict[str, Any] | Exception] | None = None,
    ) -> None:
        self.messages = StubMessagesClient(
            response_data=response_data,
            raise_exc=raise_exc,
            side_effects=side_effects,
            response_format="anthropic",
        )
        # Agents that do NOT use MCP must never touch self.beta.
        # We leave it as a MagicMock so any accidental access raises AttributeError
        # only if someone tries to *call* it.
        self.beta = MagicMock(name="beta_should_not_be_used")

    async def parse(self, **kwargs) -> Any:
        """Delegate to messages.parse for protocol compatibility."""
        return await self.messages.parse(**kwargs)


class StubNVIDIAModelClient:
    """Drop-in replacement for NVIDIA (OpenAI-compatible) client in tests."""

    def __init__(
        self,
        response_data: dict[str, Any] | None = None,
        raise_exc: Exception | None = None,
        side_effects: list[dict[str, Any] | Exception] | None = None,
    ) -> None:
        self.messages = StubMessagesClient(
            response_data=response_data,
            raise_exc=raise_exc,
            side_effects=side_effects,
            response_format="openai",
        )
        # No beta attribute needed for NVIDIA client
        self.beta = MagicMock(name="beta_should_not_be_used")

    async def parse(self, **kwargs) -> Any:
        """Delegate to messages.parse for protocol compatibility."""
        return await self.messages.parse(**kwargs)
