"""Shared pytest fixtures.

Unit tests (agent framework etc.) use an in-memory SQLite database — no Docker
required. Integration tests (migrations, seed) are marked @pytest.mark.integration
and require a running Postgres container.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

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
