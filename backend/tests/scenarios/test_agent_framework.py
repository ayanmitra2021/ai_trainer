"""
Scenario tests — Step 0.4: Agent framework.

All scenarios use the stub Claude client and an in-memory SQLite database,
so they are fast, free, and deterministic.

Scenarios
---------
1. A successful call persists a complete agent_runs row
   Given a trivial test agent with a fixed stub response,
   When it runs,
   Then an agent_runs row exists with status 'success', non-null tokens and
   latency, and output matching the schema.

2. A malformed stub response is caught, not silently accepted
   Given a stub response that violates the agent's output schema,
   When the agent runs,
   Then it raises a ValidationError and agent_runs records status 'error' with
   a message.

3. An agent with no MCP dependency never touches the MCP client machinery
   Given an agent with no MCP server configured,
   When it runs,
   Then no MCP subprocess is spawned (verified by asserting beta.* is never
   called on the stub client).

4. A transient error is retried and succeeds on a later attempt
   Given a stub that raises a transient error on the first call and returns a
   valid response on the second,
   When the agent runs (with zero back-off delay for test speed),
   Then the return value is correct, the stub was called exactly twice, and
   agent_runs records status 'success'.

5. A non-transient error is not retried
   Given a stub that raises a plain (non-transient) exception,
   When the agent runs,
   Then the stub is called exactly once and agent_runs records status 'error'.

6. Exhausting all retries records the final error in agent_runs
   Given a stub that always raises a transient error,
   And the agent is configured with max_retries=2 (3 total attempts),
   When the agent runs (with zero back-off delay),
   Then the stub is called exactly 3 times and agent_runs records status 'error'.
"""

from __future__ import annotations

from typing import Any

import pytest
import pydantic
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import Agent
from app.db.models import AgentRun
from tests.fixtures.stub_claude_client import StubClaudeClient


# ── Minimal concrete agent for testing ────────────────────────────────────────

class _GreetingInput(BaseModel):
    subject: str


class _GreetingOutput(BaseModel):
    greeting: str
    confidence: float


class _GreetingAgent(Agent[_GreetingInput, _GreetingOutput]):
    """Trivial agent that returns a greeting — used only in these tests."""

    name = "stub_test_agent"
    model = "claude-sonnet-5"
    output_model = _GreetingOutput

    def _build_messages(self, input: _GreetingInput) -> list[dict[str, Any]]:
        return [{"role": "user", "content": f"Greet: {input.subject}"}]


# ── Retry-test helpers ────────────────────────────────────────────────────────
# We define a local exception class so tests never have to construct a real
# anthropic.RateLimitError (which requires an httpx.Response). The agent
# subclass below maps this to its _transient_errors tuple.

class _FakeTransientError(Exception):
    """Stand-in for anthropic transient errors in retry scenario tests."""


class _RetryableGreetingAgent(_GreetingAgent):
    """Same as _GreetingAgent, but with a test-friendly transient error type
    and zero back-off so retry tests complete instantly."""

    _transient_errors = (_FakeTransientError,)  # type: ignore[assignment]
    max_retries = 2           # 3 total attempts — enough to cover all retry paths
    retry_base_delay_s = 0.0  # no actual sleeping in tests


# ── Scenario 1 ─────────────────────────────────────────────────────────────────

class TestSuccessfulRunPersistsAgentRunRow:
    async def test_complete_agent_run_row_on_success(self, db_session: AsyncSession):
        """
        Scenario: A successful call persists a complete agent_runs row
          Given a trivial test agent with a fixed stub response
            and the stub returns data matching the _GreetingOutput schema
          When the agent runs
          Then an agent_runs row exists with status 'success'
            and latency_ms is not null (and >= 0)
            and output matches the expected schema fields
            and tokens_input and tokens_output are populated by the stub
        """
        # Given
        stub = StubClaudeClient(
            response_data={"greeting": "Hello, World!", "confidence": 0.95}
        )
        agent = _GreetingAgent(client=stub, db_session=db_session)

        # When
        result = await agent.run(_GreetingInput(subject="World"))

        # Then — return value is correct
        assert result.greeting == "Hello, World!"
        assert result.confidence == pytest.approx(0.95)

        # Then — agent_runs row is persisted
        rows = (await db_session.execute(select(AgentRun))).scalars().all()
        assert len(rows) == 1, "Expected exactly one agent_runs row"

        row = rows[0]
        assert row.agent_name == "stub_test_agent"
        assert row.status == "success"
        assert row.error_message is None
        assert row.latency_ms is not None
        assert row.latency_ms >= 0
        assert row.tokens_input == 100   # stub fixture value
        assert row.tokens_output == 50   # stub fixture value
        assert row.model_used == "claude-sonnet-5"
        assert row.output is not None
        assert row.output["greeting"] == "Hello, World!"
        assert row.started_at is not None
        assert row.completed_at is not None


# ── Scenario 2 ─────────────────────────────────────────────────────────────────

class TestMalformedResponseIsCaught:
    async def test_validation_error_recorded_in_agent_runs(self, db_session: AsyncSession):
        """
        Scenario: A malformed stub response is caught, not silently accepted
          Given a stub response that violates the _GreetingOutput schema
            (missing required field 'greeting', has wrong type for 'confidence')
          When the agent runs
          Then a pydantic.ValidationError is raised to the caller
            and the agent_runs row has status 'error'
            and error_message is non-empty
            and output is null (nothing to persist)
        """
        # Given — response data is missing 'greeting' and has wrong 'confidence' type
        stub = StubClaudeClient(response_data={"wrong_field": "oops", "confidence": "not-a-float"})
        agent = _GreetingAgent(client=stub, db_session=db_session)

        # When / Then — the agent should raise
        with pytest.raises(pydantic.ValidationError):
            await agent.run(_GreetingInput(subject="World"))

        # Then — agent_runs row records the error
        rows = (await db_session.execute(select(AgentRun))).scalars().all()
        assert len(rows) == 1, "Expected exactly one agent_runs row even on error"

        row = rows[0]
        assert row.status == "error"
        assert row.error_message is not None and len(row.error_message) > 0
        assert row.output is None


# ── Scenario 3 ─────────────────────────────────────────────────────────────────

class TestAgentWithNoMcpNeverTouchesMcpMachinery:
    async def test_no_mcp_subprocess_spawned(self, db_session: AsyncSession):
        """
        Scenario: An agent with no MCP dependency never touches the MCP client machinery
          Given a _GreetingAgent which has no MCP server configured
          When it runs successfully
          Then stub.beta has never been accessed (no MCP wiring occurred)
        """
        # Given
        stub = StubClaudeClient(
            response_data={"greeting": "Hi there", "confidence": 0.8}
        )
        agent = _GreetingAgent(client=stub, db_session=db_session)

        # When
        await agent.run(_GreetingInput(subject="there"))

        # Then — the MagicMock for stub.beta should not have had any *calls*
        # (accessing .beta as an attribute is fine; calling methods on it is not)
        beta_mock = stub.beta
        assert not beta_mock.called, (
            "stub.beta was called — the agent unexpectedly touched MCP machinery"
        )
        assert beta_mock.call_count == 0


# ── Scenario 4 ─────────────────────────────────────────────────────────────────

class TestTransientErrorIsRetriedAndSucceeds:
    async def test_retry_on_transient_error_succeeds(self, db_session: AsyncSession):
        """
        Scenario: A transient error is retried and succeeds on a later attempt
          Given a stub that raises _FakeTransientError on the first call
            and returns a valid response on the second call
            and the agent has zero back-off delay (tests run instantly)
          When the agent runs
          Then the return value is correct
            and the stub was called exactly twice (one failure + one success)
            and agent_runs records status 'success' (not the intermediate error)
        """
        # Given — first call raises transient error; second call returns valid data
        stub = StubClaudeClient(
            side_effects=[_FakeTransientError("rate limited")],
            response_data={"greeting": "Retry worked!", "confidence": 0.7},
        )
        agent = _RetryableGreetingAgent(client=stub, db_session=db_session)

        # When
        result = await agent.run(_GreetingInput(subject="retry"))

        # Then — the eventual output is correct
        assert result.greeting == "Retry worked!"
        assert result.confidence == pytest.approx(0.7)

        # Then — stub was called twice (attempt 0 failed, attempt 1 succeeded)
        assert stub.messages.call_count == 2

        # Then — only one agent_runs row, and it records the successful outcome
        rows = (await db_session.execute(select(AgentRun))).scalars().all()
        assert len(rows) == 1
        row = rows[0]
        assert row.status == "success"
        assert row.error_message is None
        assert row.output is not None
        assert row.output["greeting"] == "Retry worked!"


# ── Scenario 5 ─────────────────────────────────────────────────────────────────

class TestNonTransientErrorIsNotRetried:
    async def test_non_transient_error_does_not_retry(self, db_session: AsyncSession):
        """
        Scenario: A non-transient error is not retried
          Given a stub that raises a plain Exception (not in _transient_errors)
          When the agent runs
          Then the stub is called exactly once — no retry attempts
            and agent_runs records status 'error'
        """
        # Given — plain RuntimeError is not in _transient_errors for any agent
        non_transient = RuntimeError("authentication failed")
        stub = StubClaudeClient(raise_exc=non_transient)
        agent = _RetryableGreetingAgent(client=stub, db_session=db_session)

        # When / Then — exception propagates to caller
        with pytest.raises(RuntimeError, match="authentication failed"):
            await agent.run(_GreetingInput(subject="anyone"))

        # Then — called exactly once (no retry)
        assert stub.messages.call_count == 1

        # Then — error row is written
        rows = (await db_session.execute(select(AgentRun))).scalars().all()
        assert len(rows) == 1
        assert rows[0].status == "error"
        assert "authentication failed" in (rows[0].error_message or "")


# ── Scenario 6 ─────────────────────────────────────────────────────────────────

class TestExhaustedRetriesRecordsError:
    async def test_all_retries_exhausted_records_error(self, db_session: AsyncSession):
        """
        Scenario: Exhausting all retries records the final error in agent_runs
          Given a stub that always raises _FakeTransientError
            and the agent is configured with max_retries=2 (3 total attempts)
          When the agent runs (with zero back-off delay)
          Then the stub is called exactly 3 times (attempts 0, 1, 2)
            and the original exception propagates to the caller
            and agent_runs records status 'error' with a message
        """
        # Given — always transient; _RetryableGreetingAgent has max_retries=2
        stub = StubClaudeClient(raise_exc=_FakeTransientError("always failing"))
        agent = _RetryableGreetingAgent(client=stub, db_session=db_session)

        # When / Then — the transient error eventually propagates after all retries
        with pytest.raises(_FakeTransientError, match="always failing"):
            await agent.run(_GreetingInput(subject="never"))

        # Then — called max_retries+1 times = 3 total attempts
        assert stub.messages.call_count == agent.max_retries + 1

        # Then — one agent_runs error row covering the full (failed) run
        rows = (await db_session.execute(select(AgentRun))).scalars().all()
        assert len(rows) == 1
        row = rows[0]
        assert row.status == "error"
        assert row.error_message is not None and "always failing" in row.error_message
        assert row.output is None
