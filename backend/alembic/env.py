"""Alembic environment — uses async SQLAlchemy engine (asyncpg)."""

import asyncio
import sys
import os
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# Make sure `app` is importable from here.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.models import Base  # noqa: E402  (after sys.path manipulation)
from app.config import settings  # noqa: E402

# ── Alembic config object ─────────────────────────────────────────────────────
config = context.config

# Resolve the database URL for migrations.
#
# Priority order:
#   1. DATABASE_URL_MIGRATE env var  — set in CI/CD (GitHub Actions secret).
#      Must use the postgresql+asyncpg:// scheme and the DIRECT Supabase
#      connection (port 5432, host db.xxxx.supabase.co) — NOT the pgBouncer
#      pooler. pgBouncer's transaction-mode pooler breaks some DDL operations.
#   2. settings.database_url         — falls back to local .env / defaults
#      (used in local development where DATABASE_URL_MIGRATE is not set).
_migrate_url: str = os.environ.get("DATABASE_URL_MIGRATE") or settings.database_url

# configparser (used internally by alembic) treats % as an interpolation
# delimiter. URL-encoded passwords contain sequences like %3D, %26, %3F which
# make configparser raise "invalid interpolation syntax". Doubling every %
# escapes them: %3D → %%3D in storage, which configparser reads back as %3D
# and passes verbatim to SQLAlchemy/asyncpg for correct URL decoding.
_migrate_url_cfg = _migrate_url.replace("%", "%%")
config.set_main_option("sqlalchemy.url", _migrate_url_cfg)

# Interpret the config file for Python logging (if present).
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# ── Offline mode ──────────────────────────────────────────────────────────────

def run_migrations_offline() -> None:
    """Generate SQL without a live DB connection (useful for review)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode (async) ───────────────────────────────────────────────────────

def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations through a synchronous bridge."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
