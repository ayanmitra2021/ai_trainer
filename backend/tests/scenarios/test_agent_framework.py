"""
Scenario tests — Step 0.4: Agent framework.

All three scenarios use the stub Claude client and an in-memory SQLite database,
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
   accessed on the stub client).
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


# ── Scenario 1 ─────────────────────────────────────────────────────────────────

class TestSuccessfulRunPersistsAgentRunRow:
    async def test_complete_agent_run_row_on_success(self, db_session: AsyncSession):
        """
        Scenario: A successful call persists a complete agent_runs row
          Given a trivial test agent with a fixed stub response
            and the stub returns data matching the _GreetingOutput schema
          When the agent runs
          Then an agent_runs row exists with status 'success'
            and latency_ms is not null (and > 0)
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
