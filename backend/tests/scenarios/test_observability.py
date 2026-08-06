"""Step 5.1 — Observability scenario.

Scenario: A recent agent error is surfaced in the observability view,
          including the error message.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AgentRun
from app.db.session import get_db
from app.main import app
from tests.conftest import apply_admin_auth_overrides


@pytest_asyncio.fixture
async def obs_client(db_session: AsyncSession, admin_session_info) -> AsyncClient:
    """AsyncClient wired to test DB with admin auth."""
    async def _get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_test_db
    apply_admin_auth_overrides(app, admin_session_info)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def _insert_agent_run(
    db: AsyncSession,
    *,
    agent_name: str = "skill_profiler",
    status: str = "success",
    error_message: str | None = None,
    latency_ms: int = 250,
    tokens_input: int = 500,
    tokens_output: int = 120,
    started_at: datetime | None = None,
) -> AgentRun:
    now = started_at or datetime.now(UTC)
    run = AgentRun(
        id=str(uuid.uuid4()),
        agent_name=agent_name,
        workflow_run_id=None,
        input={"test": True},
        output={"test": True} if status == "success" else None,
        model_used="claude-sonnet-5",
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        latency_ms=latency_ms,
        status=status,
        error_message=error_message,
        started_at=now,
        completed_at=now + timedelta(milliseconds=latency_ms),
    )
    db.add(run)
    await db.flush()
    return run


class TestObservabilityScenarios:
    async def test_recent_agent_error_is_surfaced_with_message(
        self,
        db_session: AsyncSession,
        obs_client: AsyncClient,
    ):
        """
        Scenario: A recent agent error is surfaced in the observability view,
                  including the error message.
          Given an agent_runs row with status='error' and an error_message
          When GET /api/v1/observability/agent-runs is called
          Then the response includes the run in 'recent_errors' with its error_message
          And the overall error_count and error_rate reflect the error
        """
        # Given
        error_message = "RateLimitError: 429 from Anthropic API"
        await _insert_agent_run(
            db_session,
            agent_name="correlation",
            status="error",
            error_message=error_message,
        )
        await _insert_agent_run(
            db_session,
            agent_name="skill_profiler",
            status="success",
        )
        await db_session.flush()

        # When
        response = await obs_client.get("/api/v1/observability/agent-runs")

        # Then
        assert response.status_code == 200, response.text
        data = response.json()

        assert data["total_runs"] == 2
        assert data["error_count"] == 1
        assert abs(data["error_rate"] - 0.5) < 0.01

        # Error appears in recent_errors with the message
        assert len(data["recent_errors"]) == 1
        err = data["recent_errors"][0]
        assert err["agent_name"] == "correlation"
        assert err["error_message"] == error_message

    async def test_per_agent_breakdown_included(
        self,
        db_session: AsyncSession,
        obs_client: AsyncClient,
    ):
        """
        Scenario: by_agent breakdown includes each agent that ran.
          Given two agents each with one successful run
          When GET /api/v1/observability/agent-runs is called
          Then by_agent contains one row per agent with correct counts
        """
        # Given
        await _insert_agent_run(db_session, agent_name="skill_profiler", status="success")
        await _insert_agent_run(db_session, agent_name="grader", status="success")
        await db_session.flush()

        # When
        response = await obs_client.get("/api/v1/observability/agent-runs")

        # Then
        assert response.status_code == 200
        data = response.json()
        by_name = {a["agent_name"]: a for a in data["by_agent"]}

        assert "skill_profiler" in by_name
        assert "grader" in by_name
        assert by_name["skill_profiler"]["run_count"] == 1
        assert by_name["skill_profiler"]["error_count"] == 0
        assert by_name["skill_profiler"]["error_rate"] == 0.0

    async def test_observability_requires_admin_auth(
        self,
        db_session: AsyncSession,
    ):
        """
        Guard: /observability/agent-runs returns 401/403 without auth.
        """
        # Build client with NO auth overrides
        async def _get_test_db():
            yield db_session

        app.dependency_overrides[get_db] = _get_test_db
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                response = await c.get("/api/v1/observability/agent-runs")
            # Without a session cookie the endpoint must refuse
            assert response.status_code in (401, 403)
        finally:
            app.dependency_overrides.clear()
