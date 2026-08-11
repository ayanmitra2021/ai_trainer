"""Step 3.6 / Phase 9.1 — Pulse API scenarios.

Phase 9.1 changes:
  - Removed: test_rollup_below_privacy_floor_has_null_metrics (rollups removed)
  - Removed: small_rollup fixture (rollups table dropped)
  - Added:   test_rollups_endpoint_returns_404 — /rollups no longer exists
  - Added:   test_nightly_pulse_trigger_endpoint_returns_404 — POST /pulse/run removed

Remaining scenarios:
  Scenario: Approving a drafted nudge changes its status and sets sent_at.
  Scenario: GET /rollups returns 404 — the endpoint has been removed (Phase 9.1).
  Scenario: POST /pulse/run returns 404 — the endpoint has been removed (Phase 9.1).
  Scenario: The admin-initiated nudge campaign workflow is unaffected — correlation
            snapshots and nudge routes still operate correctly.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Nudge, Practitioner
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
        Scenario: Approving a drafted nudge changes its status to sent.
          Given a nudge with status 'drafted'
          When POST /nudges/{id}/approve is called
          Then the response shows status='sent' with sent_at set
          And a subsequent GET confirms the change persisted
        """
        # Given
        assert drafted_nudge.status == "drafted"

        # When
        response = await http_client.post(f"/api/v1/nudges/{drafted_nudge.id}/approve")

        # Then
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["status"] == "sent"
        assert data["sent_at"] is not None
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
        assert matching[0]["status"] == "sent"
        assert matching[0]["sent_at"] is not None

    async def test_approving_already_sent_nudge_returns_409(
        self,
        db_session: AsyncSession,
        drafted_nudge: Nudge,
        http_client: AsyncClient,
    ):
        """
        Scenario: Approving an already-sent nudge returns a conflict error.
          Given a nudge that was already sent
          When POST /nudges/{id}/approve is called again
          Then the response is 409 Conflict
        """
        # Given — approve once (sets status to 'sent')
        drafted_nudge.status = "sent"
        await db_session.flush()

        # When — try to approve again
        response = await http_client.post(f"/api/v1/nudges/{drafted_nudge.id}/approve")

        # Then
        assert response.status_code == 409

    # ── Phase 9.1 removal scenarios ───────────────────────────────────────────

    async def test_rollups_endpoint_returns_404(
        self,
        http_client: AsyncClient,
    ):
        """
        Scenario (Phase 9.1): GET /rollups returns 404 after endpoint removal.
          Given the rollups table has been dropped and the /rollups route removed
          When GET /api/v1/rollups is called (even by an admin)
          Then the response is 404 Not Found — the endpoint no longer exists
        """
        # When
        response = await http_client.get("/api/v1/rollups")

        # Then — 404, not 200 or 403
        assert response.status_code == 404, (
            f"Expected 404 for /rollups after Phase 9.1 removal, got {response.status_code}. "
            f"Body: {response.text}"
        )

    async def test_rollup_by_id_endpoint_returns_404(
        self,
        http_client: AsyncClient,
    ):
        """
        Scenario (Phase 9.1): GET /rollups/{id} returns 404 after endpoint removal.
          Given the /rollups route has been removed
          When GET /api/v1/rollups/{some-id} is called
          Then the response is 404 Not Found
        """
        # When — any UUID will do; the route itself doesn't exist
        response = await http_client.get(f"/api/v1/rollups/{uuid.uuid4()}")

        # Then
        assert response.status_code == 404, (
            f"Expected 404 for /rollups/{{id}} after Phase 9.1 removal, got {response.status_code}"
        )

    async def test_nightly_pulse_trigger_endpoint_returns_404(
        self,
        http_client: AsyncClient,
    ):
        """
        Scenario (Phase 9.1): POST /pulse/run returns 404 after endpoint removal.
          Given the nightly_pulse trigger endpoint has been removed
          When POST /api/v1/pulse/run is called (even by an admin)
          Then the response is 404 Not Found — not a silent 200
        """
        # When
        response = await http_client.post(
            "/api/v1/pulse/run",
            json={
                "practitioner_ids": [],
                "scope": "practice",
                "scope_ref": "test",
                "period_start": "2026-08-01",
                "period_end": "2026-08-10",
            },
        )

        # Then — 404, not 200 or 422
        assert response.status_code == 404, (
            f"Expected 404 for POST /pulse/run after Phase 9.1 removal, got {response.status_code}. "
            f"The nightly_pulse trigger must not silently succeed — it should be gone. "
            f"Body: {response.text}"
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
          When GET /nudges?status=sent is called (none exist yet)
          Then the drafted nudge does NOT appear
        """
        # When — filter for drafted
        response = await http_client.get("/api/v1/nudges", params={"status": "drafted"})
        assert response.status_code == 200
        nudges = response.json()
        matching_ids = {n["id"] for n in nudges}
        assert drafted_nudge.id in matching_ids

        # When — filter for sent (none exist)
        response2 = await http_client.get("/api/v1/nudges", params={"status": "sent"})
        assert response2.status_code == 200
        nudges2 = response2.json()
        matching_ids2 = {n["id"] for n in nudges2}
        assert drafted_nudge.id not in matching_ids2
