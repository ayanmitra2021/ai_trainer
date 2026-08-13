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
    # Phase 14.1: Haiku is the only model used for all Anthropic calls in this
    # deployment.  Override via APP_ANTHROPIC_MODEL_ID in .env if needed, but
    # do not change to Sonnet/Opus without explicit cost-control approval.
    app_anthropic_model_id: str = Field(
        default="claude-haiku-4-5-20251001",
        description=(
            "Anthropic model ID enforced for all calls.  "
            "Default: claude-haiku-4-5-20251001.  "
            "Do not change to Sonnet/Opus without explicit approval."
        ),
    )

    # ── NVIDIA Nemotron ───────────────────────────────────────────────────
    nvidia_api_key: str = Field(default="", description="NVIDIA API key (required when APP_BRAIN_MODEL=NVIDIA).")
    nvidia_base_url: str = Field(
        default="https://integrate.api.nvidia.com/v1",
        description="NVIDIA API base URL (OpenAI-compatible).",
    )
    # Phase 15: two-model NVIDIA estate (Ultra = Tier 1, Lightning = Tier 2).
    # NVIDIA_MODEL_ID (singular) is deprecated — use the PRIMARY/SECONDARY vars.
    nvidia_model_id_primary: str = Field(
        default="nvidia/nemotron-3-ultra-550b-a55b",
        description="NVIDIA Tier-1 model (Ultra). Used as primary in NVIDIA mode, last fallback in ANTHROPIC mode.",
    )
    nvidia_model_id_secondary: str = Field(
        default="nvidia/nemotron-3.5-lightning-30b-a3b",
        description="NVIDIA Tier-2 model (Lightning). Fallback within the NVIDIA estate.",
    )
    # Deprecated (Phase 14 → 15): kept so old .env files don't crash.
    nvidia_model_id: str = Field(
        default="",
        description="Deprecated — use NVIDIA_MODEL_ID_PRIMARY instead.",
    )

    # ── Phase 15 timeouts ─────────────────────────────────────────────────
    nvidia_tier1_timeout_secs: int = Field(
        default=10,
        description="asyncio.wait_for timeout for Tier-1 (Ultra in NVIDIA mode, Haiku in ANTHROPIC mode).",
    )
    nvidia_tier2_timeout_secs: int = Field(
        default=20,
        description="asyncio.wait_for timeout for Tier-2 (Lightning in both modes).",
    )
    anthropic_tier_timeout_secs: int = Field(
        default=20,
        description="asyncio.wait_for timeout for the Anthropic/Haiku tier (any position in chain).",
    )

    # ── Phase 15 circuit breaker ──────────────────────────────────────────
    nvidia_circuit_breaker_threshold: int = Field(
        default=5,
        description="Consecutive NVIDIA-both-fail calls before the circuit breaker opens.",
    )
    nvidia_circuit_breaker_cooldown_secs: int = Field(
        default=120,
        description="Cooldown duration in seconds when the circuit breaker is open.",
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
