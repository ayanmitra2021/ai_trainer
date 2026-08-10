"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


# ── CORS ─────────────────────────────────────────────────────────────────────
# Must be added BEFORE any route includes.
# allow_credentials=True is required so the browser sends the session cookie on
# cross-origin requests (GitHub Pages → Render).  When credentials are allowed,
# the origin list must be explicit — "*" is rejected by browsers in that case.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz", tags=["meta"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


# ── Phase 2 routes ────────────────────────────────────────────────────────────
from app.api.routes import practitioners, skills, certifications, learning_paths

app.include_router(practitioners.router, prefix="/api/v1")
app.include_router(skills.router, prefix="/api/v1")
app.include_router(certifications.router, prefix="/api/v1")
app.include_router(learning_paths.router, prefix="/api/v1")

# ── Phase 3 routes ────────────────────────────────────────────────────────────
from app.api.routes import pulse

app.include_router(pulse.router, prefix="/api/v1")

# ── Phase 5 routes ────────────────────────────────────────────────────────────
from app.api.routes import auth, observability, admin_users

app.include_router(auth.router, prefix="/api/v1")
app.include_router(observability.router, prefix="/api/v1")
app.include_router(admin_users.router, prefix="/api/v1")

# ── Phase 6 routes ────────────────────────────────────────────────────────────
from app.api.routes import profiles

app.include_router(profiles.router, prefix="/api/v1")

# ── Phase 7 routes ────────────────────────────────────────────────────────────
from app.api.routes import nudges as nudge_routes

app.include_router(nudge_routes.router, prefix="/api/v1")
