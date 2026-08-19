"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

_log = logging.getLogger("mastery_pulse")

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


# ── Catch-all exception handler ───────────────────────────────────────────────
# Without this, unhandled exceptions escape CORSMiddleware and reach
# Starlette's outermost ServerErrorMiddleware, which generates the 500 response
# *outside* the CORS layer — so no Access-Control-Allow-Origin header is added
# and the browser sees a CORS error instead of the real 500.
# This handler runs inside CORSMiddleware so its responses always get the header.
@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Log the full validation error so it appears in Render logs for debugging.
    _log.warning("422 Validation error on %s %s: %s", request.method, request.url.path, exc.errors())
    # Pydantic v2 includes non-JSON-serialisable objects (e.g. ValueError instances)
    # inside ctx.error — stringify them so json.dumps never raises.
    safe_errors = []
    for err in exc.errors():
        err_copy = dict(err)
        if "ctx" in err_copy and "error" in err_copy.get("ctx", {}):
            err_copy["ctx"] = {
                **err_copy["ctx"],
                "error": str(err_copy["ctx"]["error"]),
            }
        safe_errors.append(err_copy)
    return JSONResponse(status_code=422, content={"detail": safe_errors})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Phase 15: catch AllProvidersUnavailableError before the generic 500 handler.
    # Must be checked here because FastAPI resolves the most-specific handler —
    # registering a separate handler for AllProvidersUnavailableError (a RuntimeError
    # subclass) after the Exception handler may not fire correctly on all FastAPI
    # versions, so we handle it inside the catch-all.
    from app.agents.model_client import AllProvidersUnavailableError
    if isinstance(exc, AllProvidersUnavailableError):
        _log.warning(
            "All LLM providers unavailable on %s %s: %s",
            request.method, request.url.path, exc,
        )
        return JSONResponse(
            status_code=503,
            content={
                "error": "all_providers_unavailable",
                "message": (
                    "All LLM providers are temporarily unavailable. "
                    "Please try again in a few minutes."
                ),
                "retry_after_seconds": 120,
            },
            headers={"Retry-After": "120"},
        )
    _log.exception("Unhandled exception on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error — check server logs for details."},
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

# ── Phase 10.2 routes ─────────────────────────────────────────────────────────
from app.api.routes import cert_domain_versions

app.include_router(cert_domain_versions.router, prefix="/api/v1")

# ── Phase 11 routes ────────────────────────────────────────────────────────────
from app.api.routes import mock_exams

app.include_router(mock_exams.router, prefix="/api/v1")

# ── Phase 13 routes ────────────────────────────────────────────────────────────
from app.api.routes import cert_discovery

app.include_router(cert_discovery.router, prefix="/api/v1")

# ── Phase 18 routes ────────────────────────────────────────────────────────────
from app.api.routes import byte_sized_lessons

app.include_router(byte_sized_lessons.router, prefix="/api/v1")
