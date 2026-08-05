"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.db.session import engine
from app.db.models import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Nothing to do at startup for now (migrations run via alembic, not here).
    yield
    # Clean up the connection pool on shutdown.
    await engine.dispose()


app = FastAPI(
    title="Mastery Pulse API",
    description=(
        "Backend for Mastery Mesh (learning loop) and Adoption Pulse (signal loop)."
    ),
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
)


@app.get("/healthz", tags=["meta"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


# Phase 2+ routes are registered here as they are built.
# from app.api.routes import practitioners, skills
# app.include_router(practitioners.router, prefix="/api/v1")
# app.include_router(skills.router, prefix="/api/v1")
