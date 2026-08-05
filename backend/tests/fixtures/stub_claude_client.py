"""Stub Claude client for agent scenario tests.

The stub is intentionally narrow — it only implements the surface the Agent
base class touches. Tests configure it with either a dict of response data
(which the stub validates against the expected output_format) or an exception
to raise, simulating API errors or validation failures.

Usage in conftest.py / tests:

    from tests.fixtures.stub_claude_client import StubClaudeClient, StubMessagesClient

    # Happy path — returns a valid response
    client = StubClaudeClient(response_data={"greeting": "hello", "score": 0.9})

    # Error path — raises on the call
    client = StubClaudeClient(raise_exc=ValueError("network timeout"))

    # Malformed — data doesn't match the output schema; the Agent catches it
    client = StubClaudeClient(response_data={"wrong_field": 99})
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pydantic
from pydantic import BaseModel


class _FakeUsage:
    input_tokens: int = 100
    output_tokens: int = 50


class _FakeParsedResponse:
    """Returned by StubMessagesClient.parse()."""

    def __init__(self, parsed: BaseModel) -> None:
        self.parsed = parsed
        self.usage = _FakeUsage()


class StubMessagesClient:
    """Implements the MessagesClient protocol — no real HTTP calls."""

    def __init__(
        self,
        response_data: dict[str, Any] | None = None,
        raise_exc: Exception | None = None,
    ) -> None:
        self._response_data = response_data or {}
        self._raise_exc = raise_exc
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
    ) -> _FakeParsedResponse:
        self.call_count += 1
        self.last_call_kwargs = dict(
            model=model,
            system=system,
            messages=messages,
            max_tokens=max_tokens,
            output_format=output_format,
            **kwargs,
        )

        if self._raise_exc is not None:
            raise self._raise_exc

        # Attempt to parse the raw dict into the expected output format.
        # If this raises ValidationError, the Agent base class will catch it
        # and record status='error' in agent_runs.
        parsed = output_format.model_validate(self._response_data)
        return _FakeParsedResponse(parsed)


class StubClaudeClient:
    """Drop-in replacement for anthropic.AsyncAnthropic in tests."""

    def __init__(
        self,
        response_data: dict[str, Any] | None = None,
        raise_exc: Exception | None = None,
    ) -> None:
        self.messages = StubMessagesClient(
            response_data=response_data,
            raise_exc=raise_exc,
        )
        # Agents that do NOT use MCP must never touch self.beta.
        # We leave it as a MagicMock so any accidental access raises AttributeError
        # only if someone tries to *call* it.
        self.beta = MagicMock(name="beta_should_not_be_used")
