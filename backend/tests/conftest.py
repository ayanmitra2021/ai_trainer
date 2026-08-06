"""Shared pytest fixtures.

Unit tests (agent framework etc.) use an in-memory SQLite database — no Postgres
required. Integration tests (migrations, seed) are marked @pytest.mark.integration
and require a locally running Postgres instance with the mastery_pulse_test database
(see README.md for setup).
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps.session import (
    SessionInfo,
    get_session,
    require_admin,
    require_admin_or_leadership,
    require_any_authenticated,
    require_practitioner,
)
from app.db.models import Base
from tests.fixtures.stub_claude_client import StubClaudeClient


# ── Database fixtures ─────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="function")
async def sqlite_engine():
    """In-memory SQLite engine — creates all tables fresh per test function."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(sqlite_engine) -> AsyncGenerator[AsyncSession, None]:
    """Async SQLite session for unit tests (no Postgres needed)."""
    session_factory = async_sessionmaker(
        bind=sqlite_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()  # never commit in unit tests — keep DB clean


# ── Integration DB fixture ────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session")
async def pg_engine():
    """Real Postgres engine — used only by @pytest.mark.integration tests."""
    test_url = os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://mastery:mastery@localhost:5432/mastery_pulse_test",
    )
    engine = create_async_engine(test_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def pg_session(pg_engine) -> AsyncGenerator[AsyncSession, None]:
    """Async Postgres session for integration tests."""
    session_factory = async_sessionmaker(
        bind=pg_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


# ── Auth override fixtures ────────────────────────────────────────────────────

@pytest.fixture
def admin_session_info() -> SessionInfo:
    """Full-admin SessionInfo for bypassing auth in API route tests."""
    return SessionInfo(
        session_id="test-admin-session-000000000000",
        identity_type="admin",
        practitioner_id=None,
        admin_user_id="test-admin-user-0000000000000",
        admin_role="admin",
        first_name="TestAdmin",
        must_change_password=False,
    )


@pytest.fixture
def leadership_session_info() -> SessionInfo:
    """Leadership SessionInfo — can see rollups/nudges but not individual data."""
    return SessionInfo(
        session_id="test-leadership-session-000000",
        identity_type="admin",
        practitioner_id=None,
        admin_user_id="test-leadership-user-0000000",
        admin_role="leadership",
        first_name="TestLeader",
        must_change_password=False,
    )


def make_practitioner_session(practitioner_id: str) -> SessionInfo:
    """Create a practitioner SessionInfo for a specific practitioner ID."""
    return SessionInfo(
        session_id=f"test-prac-session-{practitioner_id[:8]}",
        identity_type="practitioner",
        practitioner_id=practitioner_id,
        admin_user_id=None,
        admin_role=None,
        first_name="Test",
        must_change_password=False,
    )


def apply_admin_auth_overrides(app_instance, admin_info: SessionInfo) -> None:
    """Override all auth deps in the given FastAPI app to use admin_info.

    Call this inside test client fixtures before constructing AsyncClient.
    Typically paired with app.dependency_overrides.clear() in teardown.
    """
    app_instance.dependency_overrides[get_session] = lambda: admin_info
    app_instance.dependency_overrides[require_any_authenticated] = lambda: admin_info
    app_instance.dependency_overrides[require_admin] = lambda: admin_info
    app_instance.dependency_overrides[require_admin_or_leadership] = lambda: admin_info
    app_instance.dependency_overrides[require_practitioner] = lambda: admin_info


def apply_leadership_auth_overrides(app_instance, leadership_info: SessionInfo) -> None:
    """Override auth deps for a leadership session — does NOT bypass require_admin.

    Use this when a test needs to assert that require_admin correctly rejects
    leadership-role callers.  Only require_admin_or_leadership is passed through;
    require_admin still runs its real role check (which will return 403 for leadership).
    """
    app_instance.dependency_overrides[get_session] = lambda: leadership_info
    app_instance.dependency_overrides[require_any_authenticated] = lambda: leadership_info
    app_instance.dependency_overrides[require_admin_or_leadership] = lambda: leadership_info
    app_instance.dependency_overrides[require_practitioner] = lambda: leadership_info
    # require_admin is intentionally NOT overridden so role enforcement is tested


# ── Stub Claude client fixture ────────────────────────────────────────────────

@pytest.fixture
def stub_client_factory():
    """Factory for creating StubClaudeClient instances with custom data."""
    def _make(
        response_data: dict[str, Any] | None = None,
        raise_exc: Exception | None = None,
    ) -> StubClaudeClient:
        return StubClaudeClient(response_data=response_data, raise_exc=raise_exc)
    return _make
