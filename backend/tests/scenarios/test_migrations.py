"""
Scenario tests — Step 0.2: Database migrations.

These are integration tests that require a running Postgres container.
Run with:
    py -m pytest -m integration tests/scenarios/test_migrations.py

Scenarios
---------
1. Running migrations twice is safe
   Given a fresh database,
   When alembic upgrade head runs twice in a row,
   Then the second run makes no changes and exits cleanly.

2. Downgrade reverses cleanly
   Given the migration has been applied,
   When alembic downgrade base runs,
   Then none of this migration's tables remain.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent  # backend/


def _alembic(*args: str) -> subprocess.CompletedProcess:
    """Run an alembic command from the backend directory."""
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=str(BACKEND_DIR),
        capture_output=True,
        text=True,
        check=False,
    )


PHASE0_TABLES = {
    "practitioners",
    "skills",
    "skill_profile_events",
    "skill_profile_snapshots",
    "workflow_runs",
    "agent_runs",
}


@pytest.mark.integration
class TestMigrationIdempotency:
    async def test_double_upgrade_is_safe(self):
        """
        Scenario: Running migrations twice is safe
          Given a fresh database (reset before the test suite via pg_engine fixture)
          When alembic upgrade head runs a first time
          Then it completes without error
          When alembic upgrade head runs a second time
          Then it also completes without error (nothing to do)
        """
        # First upgrade
        result1 = _alembic("upgrade", "head")
        assert result1.returncode == 0, (
            f"First alembic upgrade head failed:\n{result1.stderr}"
        )

        # Second upgrade — should be a no-op
        result2 = _alembic("upgrade", "head")
        assert result2.returncode == 0, (
            f"Second alembic upgrade head failed:\n{result2.stderr}"
        )


@pytest.mark.integration
class TestMigrationDowngrade:
    async def test_downgrade_reverses_cleanly(self):
        """
        Scenario: Downgrade reverses cleanly
          Given the migration has been applied (upgrade head)
          When alembic downgrade base runs
          Then none of this migration's tables remain in the database

        Note: alembic uses settings.database_url (mastery_pulse), NOT mastery_pulse_test.
        We verify against the same DB alembic actually ran against.
        """
        # alembic env.py reads settings.database_url — use that for verification too.
        from app.config import settings as app_settings
        alembic_db_url = app_settings.database_url  # e.g. asyncpg://…/mastery_pulse

        # Ensure we're at head first
        result_up = _alembic("upgrade", "head")
        assert result_up.returncode == 0, (
            f"alembic upgrade head failed before downgrade test:\n{result_up.stderr}"
        )

        # Downgrade to base
        result_down = _alembic("downgrade", "base")
        assert result_down.returncode == 0, (
            f"alembic downgrade base failed:\n{result_down.stderr}"
        )

        # Verify tables are gone — check the SAME database alembic ran against
        engine = create_async_engine(alembic_db_url, echo=False)
        try:
            async with engine.connect() as conn:
                existing_tables = await conn.run_sync(
                    lambda sync_conn: inspect(sync_conn).get_table_names()
                )
        finally:
            await engine.dispose()

        remaining = PHASE0_TABLES & set(existing_tables)
        assert not remaining, (
            f"These tables were not removed by downgrade: {remaining}"
        )
