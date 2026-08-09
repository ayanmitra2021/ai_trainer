#!/usr/bin/env bash
# Mastery Pulse — full deployment script
# Deploys: Postgres migrations (Supabase) -> Backend (Render) -> Frontend (GitHub Pages)
#
# Called by .github/workflows/deploy.yml, but can also be run locally:
#   export DATABASE_URL_MIGRATE="postgresql://postgres.xxxx:[password]@aws-0-region.pooler.supabase.com:5432/postgres"
#   export RENDER_DEPLOY_HOOK_URL="https://api.render.com/deploy/srv-xxxx?key=xxxx"
#   bash scripts/deploy.sh
#
# Required environment variables:
#   DATABASE_URL_MIGRATE     - DIRECT (port 5432) Supabase connection string.
#                              Must use the postgresql+asyncpg:// scheme (the
#                              migration env.py runs an async engine). Use the
#                              DIRECT host (db.xxxx.supabase.co:5432), NOT the
#                              pgBouncer pooler (port 6543) — pooler's
#                              transaction mode can break DDL migrations.
#                              Special characters in the password MUST be
#                              URL-encoded: % → %25, = → %3D, ? → %3F, & → %26
#                              Example:
#                                postgresql+asyncpg://postgres:p%40ssw0rd@db.xxx.supabase.co:5432/postgres
#   RENDER_DEPLOY_HOOK_URL   - Render service's Deploy Hook URL
#                              (Render dashboard -> service -> Settings -> Deploy Hook)
#
# Optional flags:
#   --skip-migrate      skip the DB migration step (e.g. no schema changes this run)
#   --skip-backend       skip triggering the Render deploy
#   --skip-frontend       skip building/publishing GitHub Pages

set -euo pipefail

# ── Auto-load local deploy credentials (local runs only) ─────────────────────
# If scripts/.env.deploy exists, source it before anything else so
# DATABASE_URL_MIGRATE and RENDER_DEPLOY_HOOK_URL are available.
# That file is gitignored — never committed. Copy .env.deploy.example to
# .env.deploy and fill in your real values.
_DEPLOY_ENV="$(dirname "${BASH_SOURCE[0]}")/.env.deploy"
if [ -f "$_DEPLOY_ENV" ]; then
  echo "Loading deploy credentials from scripts/.env.deploy"
  set -a            # auto-export every var that gets set
  # shellcheck disable=SC1090
  source "$_DEPLOY_ENV"
  set +a
fi
# ─────────────────────────────────────────────────────────────────────────────

SKIP_MIGRATE=false
SKIP_BACKEND=false
SKIP_FRONTEND=false

for arg in "$@"; do
  case $arg in
    --skip-migrate) SKIP_MIGRATE=true ;;
    --skip-backend) SKIP_BACKEND=true ;;
    --skip-frontend) SKIP_FRONTEND=true ;;
    "") ;;  # ignore empty args passed in from the workflow's conditional expressions
    *) echo "Unknown flag: $arg"; exit 1 ;;
  esac
done

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() { echo -e "\n=== $1 ==="; }

# ── Resolve alembic invocation ────────────────────────────────────────────────
# In CI (GitHub Actions) alembic lands directly on PATH after `pip install .`.
# Locally on Windows/Git Bash the Python Scripts directory is often absent from
# the bash PATH, so we walk through candidates in priority order.
# Critically: we only accept a Python candidate if alembic is *importable*
# from it — prevents accidentally picking the system python3 that has no alembic.
#   py / py.exe  – Windows Python Launcher (try both; Git Bash needs .exe sometimes)
#   python3      – standard Linux/macOS
#   python       – last-resort fallback
if command -v alembic &>/dev/null; then
  ALEMBIC_CMD="alembic"
else
  ALEMBIC_CMD=""
  for _PY in py py.exe python3 python; do
    if command -v "$_PY" &>/dev/null 2>&1 \
        && "$_PY" -c "import alembic" &>/dev/null 2>&1; then
      ALEMBIC_CMD="$_PY -m alembic"
      break
    fi
  done
  if [ -z "$ALEMBIC_CMD" ]; then
    echo "ERROR: Cannot find a Python interpreter with alembic installed."
    echo "  Install backend dependencies first:"
    echo "    cd backend && pip install ."
    exit 1
  fi
fi
echo "Using alembic as: $ALEMBIC_CMD"
# ─────────────────────────────────────────────────────────────────────────────

# ---------------------------------------------------------------------------
# 1. Database migrations (Alembic, against Supabase direct connection)
# ---------------------------------------------------------------------------
if [ "$SKIP_MIGRATE" = false ]; then
  log "[1/3] Running database migrations"

  if [ -z "${DATABASE_URL_MIGRATE:-}" ]; then
    echo "ERROR: DATABASE_URL_MIGRATE is not set. Aborting."
    exit 1
  fi

  cd "$ROOT_DIR/backend"

  # alembic/env.py picks up DATABASE_URL_MIGRATE automatically and builds an
  # async engine (asyncpg). Use the direct Supabase connection (port 5432).
  $ALEMBIC_CMD upgrade head

  cd "$ROOT_DIR"
  echo "Migrations applied successfully."
else
  log "[1/3] Skipped (--skip-migrate)"
fi

# ---------------------------------------------------------------------------
# 2. Backend deploy (Render, via Deploy Hook)
# ---------------------------------------------------------------------------
if [ "$SKIP_BACKEND" = false ]; then
  log "[2/3] Triggering Render backend deploy"

  if [ -z "${RENDER_DEPLOY_HOOK_URL:-}" ]; then
    echo "ERROR: RENDER_DEPLOY_HOOK_URL is not set. Aborting."
    exit 1
  fi

  HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$RENDER_DEPLOY_HOOK_URL")

  if [ "$HTTP_STATUS" != "200" ] && [ "$HTTP_STATUS" != "201" ]; then
    echo "ERROR: Render deploy hook returned HTTP $HTTP_STATUS"
    exit 1
  fi

  echo "Render deploy triggered successfully (HTTP $HTTP_STATUS)."
  echo "Note: Render builds asynchronously — check the Render dashboard's Events tab for build progress."
else
  log "[2/3] Skipped (--skip-backend)"
fi

# ---------------------------------------------------------------------------
# 3. Frontend build & deploy (GitHub Pages)
# ---------------------------------------------------------------------------
if [ "$SKIP_FRONTEND" = false ]; then
  log "[3/3] Building and deploying frontend to GitHub Pages"

  cd "$ROOT_DIR/frontend"

  # gh-pages must be a devDependency in frontend/package.json:
  #   npm install --save-dev gh-pages
  # If it's missing, this step will still work via npx (auto-downloads it),
  # but installing it explicitly avoids that extra download on every run.
  npm ci
  npm run build
  npx --yes gh-pages -d dist -u "github-actions-bot <github-actions-bot@users.noreply.github.com>"

  cd "$ROOT_DIR"
  echo "Frontend published to GitHub Pages."
else
  log "[3/3] Skipped (--skip-frontend)"
fi

log "Deployment pipeline complete."