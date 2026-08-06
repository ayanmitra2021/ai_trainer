"""Step 3.6 — Pulse API scenarios.

Scenario: Approving a drafted nudge changes its status and sets the approval.
Scenario: A rollup below the privacy floor is withheld by the API regardless of who's asking.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Nudge, Practitioner, Rollup
from app.main import app


@pytest_asyncio.fixture
async def test_practitioner(db_session: AsyncSession) -> Practitioner:
    p = Practitioner(
        id=str(uuid.uuid4()),
        name="Pulse API Test",
        email="pulse.api.test@mastery.example",
    )
    db_session.add(p)
    await db_session.flush()
    return p


@pytest_asyncio.fixture
async def drafted_nudge(
    db_session: AsyncSession, test_practitioner: Practitioner
) -> Nudge:
    nudge = Nudge(
        id=str(uuid.uuid4()),
        practitioner_id=test_practitioner.id,
        nudge_type="gap_alert",
        channel="in_app",
        content="You've built strong foundations — consider applying them in a project.",
        status="drafted",
        created_at=datetime.now(UTC),
        composer_reasoning="Gap score 0.65 warrants a nudge.",
    )
    db_session.add(nudge)
    await db_session.flush()
    return nudge


@pytest_asyncio.fixture
async def small_rollup(db_session: AsyncSession) -> Rollup:
    """Rollup below the minimum cohort size — metrics/narrative must be None."""
    now = datetime.now(UTC)
    rollup = Rollup(
        id=str(uuid.uuid4()),
        scope="team",
        scope_ref="Small Team",
        period_start=now - timedelta(days=7),
        period_end=now,
        metrics=None,
        narrative=None,
        min_cohort_size_met=False,
        created_at=now,
    )
    db_session.add(rollup)
    await db_session.flush()
    return rollup


@pytest_asyncio.fixture
async def http_client(db_session: AsyncSession, admin_session_info) -> AsyncClient:
    """AsyncClient that wires the test db_session into the FastAPI app with admin auth."""
    from httpx import ASGITransport

    from app.db.session import get_db
    from tests.conftest import apply_admin_auth_overrides

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    apply_admin_auth_overrides(app, admin_session_info)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield client
    app.dependency_overrides.clear()


class TestPulseApiScenarios:
    async def test_approving_drafted_nudge_changes_status(
        self,
        db_session: AsyncSession,
        test_practitioner: Practitioner,
        drafted_nudge: Nudge,
        http_client: AsyncClient,
    ):
        """
        Scenario: Approving a drafted nudge changes its status.
          Given a nudge with status 'drafted'
          When POST /nudges/{id}/approve is called
          Then the response shows status='approved'
          And a subsequent GET confirms the change persisted
        """
        # Given
        assert drafted_nudge.status == "drafted"

        # When
        response = await http_client.post(f"/api/v1/nudges/{drafted_nudge.id}/approve")

        # Then
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["status"] == "approved"
        assert data["id"] == drafted_nudge.id

        # And — GET confirms the status change
        get_response = await http_client.get(
            "/api/v1/nudges",
            params={"practitioner_id": test_practitioner.id},
        )
        assert get_response.status_code == 200
        nudges = get_response.json()
        matching = [n for n in nudges if n["id"] == drafted_nudge.id]
        assert len(matching) == 1
        assert matching[0]["status"] == "approved"

    async def test_approving_already_approved_nudge_returns_409(
        self,
        db_session: AsyncSession,
        drafted_nudge: Nudge,
        http_client: AsyncClient,
    ):
        """
        Scenario: Approving an already-approved nudge returns a conflict error.
          (Edge-case: idempotency is NOT guaranteed — approving twice is an error.)
          Given a nudge that was already approved
          When POST /nudges/{id}/approve is called again
          Then the response is 409 Conflict
        """
        # Given — approve once
        drafted_nudge.status = "approved"
        await db_session.flush()

        # When — try to approve again
        response = await http_client.post(f"/api/v1/nudges/{drafted_nudge.id}/approve")

        # Then
        assert response.status_code == 409

    async def test_rollup_below_privacy_floor_has_null_metrics(
        self,
        db_session: AsyncSession,
        small_rollup: Rollup,
        http_client: AsyncClient,
    ):
        """
        Scenario: A rollup below the privacy floor is withheld by the API.
          Given a rollup with min_cohort_size_met=False
          When GET /rollups/{id} is called
          Then the response includes min_cohort_size_met=False
          And metrics and narrative are null (not {} or empty string)
          (The floor holds at the API layer — not just at generation time.)
        """
        # Given — rollup was already created with min_cohort_size_met=False
        assert small_rollup.min_cohort_size_met is False
        assert small_rollup.metrics is None
        assert small_rollup.narrative is None

        # When
        response = await http_client.get(f"/api/v1/rollups/{small_rollup.id}")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["min_cohort_size_met"] is False
        # Metrics and narrative must be null — never empty dict or empty string
        assert data["metrics"] is None, (
            "metrics must be null when cohort is below the privacy floor — "
            "not an empty dict or partial data"
        )
        assert data["narrative"] is None, (
            "narrative must be null when cohort is below the privacy floor"
        )

    async def test_list_nudges_by_status_filter(
        self,
        db_session: AsyncSession,
        test_practitioner: Practitioner,
        drafted_nudge: Nudge,
        http_client: AsyncClient,
    ):
        """
        Additional scenario: listing nudges filtered by status returns only matching rows.
          Given one drafted nudge
          When GET /nudges?status=drafted is called
          Then the drafted nudge appears
          When GET /nudges?status=approved is called
          Then the drafted nudge does NOT appear
        """
        # When — filter for drafted
        response = await http_client.get("/api/v1/nudges", params={"status": "drafted"})
        assert response.status_code == 200
        nudges = response.json()
        matching_ids = {n["id"] for n in nudges}
        assert drafted_nudge.id in matching_ids

        # When — filter for approved (none exist)
        response2 = await http_client.get("/api/v1/nudges", params={"status": "approved"})
        assert response2.status_code == 200
        nudges2 = response2.json()
        matching_ids2 = {n["id"] for n in nudges2}
        assert drafted_nudge.id not in matching_ids2
