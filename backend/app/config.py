"""Application configuration — reads from environment / .env file."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve the project root (.env lives there) regardless of the working
# directory uvicorn is launched from.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
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

    # ── Model Provider ─────────────────────────────────────────────────────
    # APP_BRAIN_MODEL=ANTHROPIC (default) | NVIDIA
    app_brain_model: str = Field(
        default="ANTHROPIC",
        description="LLM provider: ANTHROPIC or NVIDIA",
    )

    # ── Anthropic ─────────────────────────────────────────────────────────
    anthropic_api_key: str = Field(default="", description="Anthropic API key.")

    # ── NVIDIA Nemotron ───────────────────────────────────────────────────
    nvidia_api_key: str = Field(default="", description="NVIDIA API key (required when APP_BRAIN_MODEL=NVIDIA).")
    nvidia_base_url: str = Field(
        default="https://integrate.api.nvidia.com/v1",
        description="NVIDIA API base URL (OpenAI-compatible).",
    )
    nvidia_model_id: str = Field(
        default="nvidia/nemotron-3-ultra-550b-a55b",
        description=(
            "NVIDIA NIM model ID. Defaults to Nemotron 3 Ultra 550B — the original project-plan model. "
            "Override via NVIDIA_MODEL_ID in .env. "
            "Run tools/check_nvidia.py to discover which models your API key can reach."
        ),
    )

    # ── App ───────────────────────────────────────────────────────────────
    environment: str = Field(default="development")
    debug: bool = Field(default=False)

    # ── CORS ─────────────────────────────────────────────────────────────
    # Comma-separated list of allowed origins for the CORS middleware.
    # Must include the GitHub Pages origin in production, and localhost for dev.
    # Set ALLOWED_ORIGINS on Render to override (no trailing slashes).
    # Example: ALLOWED_ORIGINS=https://ayanmitra2021.github.io,http://localhost:5173
    allowed_origins: str = Field(
        default="https://ayanmitra2021.github.io,http://localhost:5173",
        description="Comma-separated CORS allowed origins.",
    )

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    # ── Auth ──────────────────────────────────────────────────────────────
    session_cookie_name: str = Field(default="mastery_session")
    admin_session_timeout_hours: int = Field(
        default=8,
        description="Hours before an admin/leadership session expires from inactivity.",
    )

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
