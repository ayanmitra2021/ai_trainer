"""Application configuration — reads from environment / .env file."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://mastery:mastery@localhost:5432/mastery_pulse",
        description="Async SQLAlchemy URL for the app (asyncpg driver).",
    )
    alembic_database_url: str = Field(
        default="postgresql+psycopg2://mastery:mastery@localhost:5432/mastery_pulse",
        description="Sync SQLAlchemy URL for Alembic migrations (psycopg2 driver).",
    )

    # ── Anthropic ─────────────────────────────────────────────────────────
    anthropic_api_key: str = Field(default="", description="Anthropic API key.")

    # ── App ───────────────────────────────────────────────────────────────
    environment: str = Field(default="development")
    debug: bool = Field(default=False)

    # ── Test ──────────────────────────────────────────────────────────────
    test_database_url: str = Field(
        default="sqlite+aiosqlite:///:memory:",
        description=(
            "Database URL used by unit tests. Defaults to in-memory SQLite; "
            "set to a real Postgres URL when running @pytest.mark.integration tests."
        ),
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


settings = get_settings()
