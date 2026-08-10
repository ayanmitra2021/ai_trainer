"""Async SQLAlchemy engine and session factory."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    # statement_cache_size=0 disables asyncpg's prepared-statement cache.
    # Required when DATABASE_URL points at Supabase's pgBouncer pooler
    # (port 6543, transaction mode): pgBouncer does not preserve prepared
    # statements across connections so asyncpg's cache causes
    # DuplicatePreparedStatementError on the second request.
    # This has no effect when using the direct connection or session-mode pooler.
    connect_args={"statement_cache_size": 0},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an async database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
