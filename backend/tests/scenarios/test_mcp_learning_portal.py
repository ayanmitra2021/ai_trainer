"""
Scenario tests — Step 1.1: mcp-learning-portal MCP server.

All tests use a real stdio_client / ClientSession round-trip to verify the MCP
wire protocol, not just the underlying Python functions.

Scenarios
---------
1. get_certifications returns a known practitioner's certification
2. A practitioner with no data returns an empty list, not an error
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "learning_portal"
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


def _server_params() -> StdioServerParameters:
    """StdioServerParameters pointing the server at the test fixture directory."""
    existing = os.environ.get("PYTHONPATH", "")
    pythonpath = str(BACKEND_DIR) + (os.pathsep + existing if existing else "")
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.mcp_servers.learning_portal.server"],
        env={
            **os.environ,
            "PYTHONPATH": pythonpath,
            "LEARNING_PORTAL_DATA_DIR": str(FIXTURES_DIR),
        },
    )


class TestGetCertificationsKnownPractitioner:
    async def test_known_practitioner_certification_returned(self):
        """
        Scenario: get_certifications returns a known practitioner's certification
          Given the fixture export contains one CCAF certification for practitioner-alice
          When get_certifications is called through a real stdio ClientSession
          Then the response is not an error
            and it contains exactly one certification
            and that certification has certification_code "CCAF"
            and it has a non-empty covered_skills list
        """
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "get_certifications",
                    {"practitioner_id": "practitioner-alice"},
                )

                assert not result.isError, f"Tool returned an error: {result}"
                assert result.content
                payload = json.loads(result.content[0].text)

                assert payload["practitioner_id"] == "practitioner-alice"
                certs = payload["certifications"]
                assert len(certs) == 1
                assert certs[0]["certification_code"] == "CCAF"
                assert len(certs[0]["covered_skills"]) > 0


class TestUnknownPractitionerReturnsEmptyLists:
    async def test_all_tools_return_empty_for_unknown_practitioner(self):
        """
        Scenario: A practitioner with no data returns an empty list, not an error
          Given "practitioner-unknown" has no records in any fixture file
          When each of the three tools is called for that practitioner
          Then each returns an empty list, not a protocol error or exception
        """
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                r = await session.call_tool(
                    "get_certifications",
                    {"practitioner_id": "practitioner-unknown"},
                )
                assert not r.isError
                assert json.loads(r.content[0].text)["certifications"] == []

                r = await session.call_tool(
                    "get_course_completions",
                    {"practitioner_id": "practitioner-unknown"},
                )
                assert not r.isError
                assert json.loads(r.content[0].text)["completions"] == []

                r = await session.call_tool(
                    "get_self_assessment",
                    {"practitioner_id": "practitioner-unknown"},
                )
                assert not r.isError
                assert json.loads(r.content[0].text)["assessments"] == []
