"""
Scenario tests — Step 1.2: mcp-usage-signals MCP server.

All tests use a real stdio_client / ClientSession round-trip to verify the MCP
wire protocol and confirm the mapping rule fires (or correctly doesn't fire).

Scenarios
---------
1. A mapped session produces the right skill mapping
2. An ambiguous session is returned unmapped, not guessed
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "usage_signals"
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


def _server_params() -> StdioServerParameters:
    """StdioServerParameters pointing the server at the test fixture directory."""
    existing = os.environ.get("PYTHONPATH", "")
    pythonpath = str(BACKEND_DIR) + (os.pathsep + existing if existing else "")
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.mcp_servers.usage_signals.server"],
        env={
            **os.environ,
            "PYTHONPATH": pythonpath,
            "USAGE_SIGNALS_DATA_DIR": str(FIXTURES_DIR),
        },
    )


class TestMappedSessionProducesSkillMapping:
    async def test_rag_session_maps_to_rag_fundamentals(self):
        """
        Scenario: A mapped session produces the right skill mapping
          Given a fixture session with project_type "rag-pipeline"
            and description mentioning retrieval and embeddings
          When get_claude_code_sessions is called through a real stdio ClientSession
          Then sess-001 has skill_id "rag_fundamentals" and confidence is not null
        """
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "get_claude_code_sessions",
                    {"practitioner_id": "practitioner-alice"},
                )

                assert not result.isError, f"Tool returned an error: {result}"
                assert result.content
                sessions = json.loads(result.content[0].text)["sessions"]

                rag = next((s for s in sessions if s["session_id"] == "sess-001"), None)
                assert rag is not None, "sess-001 not found in returned sessions"
                assert rag["skill_id"] == "rag_fundamentals", (
                    f"Expected 'rag_fundamentals', got {rag['skill_id']!r}"
                )
                assert rag["confidence"] is not None


class TestAmbiguousSessionReturnedUnmapped:
    async def test_neutral_session_has_null_skill_mapping(self):
        """
        Scenario: An ambiguous session is returned unmapped, not guessed
          Given a fixture session with project_type "general"
            and a neutral description (CSV parser bug fix — no skill keywords)
          When get_claude_code_sessions is called through a real stdio ClientSession
          Then sess-002 has skill_id null and confidence null
        """
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "get_claude_code_sessions",
                    {"practitioner_id": "practitioner-alice"},
                )

                assert not result.isError, f"Tool returned an error: {result}"
                assert result.content
                sessions = json.loads(result.content[0].text)["sessions"]

                ambiguous = next(
                    (s for s in sessions if s["session_id"] == "sess-002"), None
                )
                assert ambiguous is not None, "sess-002 not found in returned sessions"
                assert ambiguous["skill_id"] is None, (
                    f"Expected null skill_id, got {ambiguous['skill_id']!r}"
                )
                assert ambiguous["confidence"] is None
