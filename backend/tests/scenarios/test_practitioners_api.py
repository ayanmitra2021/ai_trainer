"""Step 2.1 — Practitioners API scenarios.

Scenario: Creating then fetching a practitioner returns matching data.
Scenario: Fetching a nonexistent practitioner returns 404, not a 500.
Scenario: The skill graph endpoint preserves hierarchy.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db.models import Skill
from app.db.session import get_db


# Override the DB dependency to use our test SQLite session
async def override_get_db(db_session):
    async def _override():
        yield db_session
    return _override


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """AsyncClient wired to the test SQLite DB."""
    app.dependency_overrides[get_db] = lambda: db_session.__aiter__().__anext__()

    # Simpler approach: override get_db to yield the existing session
    async def _get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_test_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


class TestCreateAndFetchPractitioner:
    async def test_create_then_fetch_returns_matching_data(self, client: AsyncClient):
        """
        Scenario: Creating then fetching a practitioner returns matching data.
          Given a valid practitioner payload
          When POST /api/v1/practitioners is called
          Then a 201 is returned with the new practitioner
          And GET /api/v1/practitioners/{id} returns matching data
        """
        # Given
        payload = {
            "name": "Test Practitioner",
            "email": "test.practitioner@example.com",
            "role": "Consultant",
            "practice": "AI&E",
            "seniority_level": "mid",
        }

        # When
        create_response = await client.post("/api/v1/practitioners", json=payload)

        # Then
        assert create_response.status_code == 201
        created = create_response.json()
        assert created["name"] == payload["name"]
        assert created["email"] == payload["email"]
        assert created["role"] == payload["role"]
        assert "id" in created

        # And
        fetch_response = await client.get(f"/api/v1/practitioners/{created['id']}")
        assert fetch_response.status_code == 200
        fetched = fetch_response.json()
        assert fetched["id"] == created["id"]
        assert fetched["name"] == created["name"]
        assert fetched["email"] == created["email"]


class TestNotFoundReturns404:
    async def test_fetching_nonexistent_practitioner_returns_404(self, client: AsyncClient):
        """
        Scenario: Fetching a nonexistent practitioner returns 404, not a 500.
          Given a practitioner ID that does not exist in the database
          When GET /api/v1/practitioners/{id} is called
          Then the response status is 404
          And the body contains a meaningful error detail, not a server error
        """
        # Given
        nonexistent_id = "00000000-0000-0000-0000-000000000000"

        # When
        response = await client.get(f"/api/v1/practitioners/{nonexistent_id}")

        # Then
        assert response.status_code == 404
        body = response.json()
        assert "detail" in body
        # Must NOT be a 500 (server error would have no "detail" field in this shape)
        assert response.status_code != 500


class TestSkillGraphHierarchy:
    async def test_skill_graph_preserves_parent_child_references(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """
        Scenario: The skill graph endpoint preserves hierarchy.
          Given skills with parent/child relationships seeded in the database
          When GET /api/v1/skills is called
          Then child skills correctly reference their parent_skill_id
        """
        # Given — seed a small skill hierarchy directly into the test DB
        parent_skill = Skill(
            id="parent-skill-id-001",
            name="Parent Skill",
            category="Test Category",
            parent_skill_id=None,
            description="A parent skill",
        )
        child_skill = Skill(
            id="child-skill-id-001",
            name="Child Skill",
            category="Test Category",
            parent_skill_id="parent-skill-id-001",
            description="A child skill",
        )
        db_session.add(parent_skill)
        db_session.add(child_skill)
        await db_session.flush()

        # When
        response = await client.get("/api/v1/skills")

        # Then
        assert response.status_code == 200
        skills = response.json()
        skill_by_id = {s["id"]: s for s in skills}

        assert "parent-skill-id-001" in skill_by_id
        assert "child-skill-id-001" in skill_by_id

        child = skill_by_id["child-skill-id-001"]
        assert child["parent_skill_id"] == "parent-skill-id-001"

        parent = skill_by_id["parent-skill-id-001"]
        assert parent["parent_skill_id"] is None
