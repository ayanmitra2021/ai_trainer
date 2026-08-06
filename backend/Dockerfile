# syntax=docker/dockerfile:1
# Mastery Pulse — backend (FastAPI + Uvicorn)
#
# Expects Postgres as an external managed service — not included here.
# Build:  docker build -t mastery-pulse-backend ./backend
# Run:    docker run -p 8000:8000 --env-file ../.env mastery-pulse-backend

FROM python:3.11-slim AS base

# System deps for psycopg2 and bcrypt
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Dependencies ──────────────────────────────────────────────────────────────
FROM base AS deps

COPY pyproject.toml ./
# Install the package in editable mode so app.* imports resolve
RUN pip install --no-cache-dir -e ".[dev]" 2>/dev/null || pip install --no-cache-dir -e .

# ── Runtime image ─────────────────────────────────────────────────────────────
FROM deps AS runtime

COPY . .

EXPOSE 8000

# Apply migrations then start the server.
# In production you may prefer to run migrations as a separate pre-deploy job.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
