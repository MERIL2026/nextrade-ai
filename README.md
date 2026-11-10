# NEXTRADE AI — Phase 1 Engineering Foundation

NEXTRADE AI is an AI-powered multi-market financial intelligence and equity research platform targeting Indian (**NSE**, **BSE**) and US (**NYSE**, **NASDAQ**) markets.

> **Research & Decision-Support Notice:** NEXTRADE AI is strictly a financial research, analytics, and decision-support platform. It does **not** perform automatic live trade execution and does **not** promise guaranteed financial returns or investment certainty. Phase 1 establishes the verified engineering foundation only—zero fake market prices, synthetic financials, or predictive ML models are included.

---

## Architecture Overview (Phase 1 Baseline)

NEXTRADE AI is structured as a modular monolith with isolated web, API, asynchronous worker/scheduler, PostgreSQL, and Redis services:

- **Frontend (`apps/web/`):** Next.js 16, React 19, TypeScript (strict), Tailwind CSS v4, institutional UI primitives, Vitest + React Testing Library, and Playwright E2E smoke coverage. Queries real FastAPI health telemetry via both SSR (`INTERNAL_API_BASE_URL`) and browser client probes (`NEXT_PUBLIC_API_BASE_URL`).
- **API Backend (`services/api/`):** Python 3.12 modular monolith built with FastAPI, Pydantic v2 (`pydantic-settings` fail-closed configuration), SQLAlchemy 2 async (`psycopg`), Alembic schema migrations, structured secret-redacting UTC JSON logging, request correlation (`X-Request-ID`), security headers, explicit CORS allowlists, and live dependency readiness checks (`GET /health` and `GET /api/v1/health`).
- **Async Worker & Scheduler (`services/worker/`):** Celery 5 worker and Beat scheduler backed by authenticated Redis for idempotent health/operational tasks (`ops.heartbeat`) and future market-ingestion pipelines.
- **Database (`PostgreSQL 18`):** System of record with strict role separation (`nextrade_owner` schema owner for Alembic migrations vs. non-superuser `nextrade_app` runtime application role) and an initial reversible bootstrap migration (`0001_bootstrap_schemas`) creating the 9 logical schemas:
  `core`, `market`, `fundamental`, `analytics`, `ml`, `news`, `portfolio`, `engagement`, `ops`.
- **Cache & Coordination (`Redis 8`):** Ephemeral cache and Celery broker/backend protected with authentication (`--requirepass`).

See [`infrastructure/adrs/ADR-0001-phase1-foundation-decisions.md`](infrastructure/adrs/ADR-0001-phase1-foundation-decisions.md) and [`infrastructure/adrs/CONFLICT_REGISTER.md`](infrastructure/adrs/CONFLICT_REGISTER.md) for documented architectural decisions and cross-document Phase 2+ items intentionally kept open.

---

## Repository Structure

```text
nextrade-ai/
├── apps/
│   └── web/                    # Next.js 16 + TypeScript frontend
├── services/
│   ├── api/                    # FastAPI modular monolith + SQLAlchemy 2 + Alembic
│   └── worker/                 # Celery worker + Beat scheduler skeleton
├── packages/                   # Reserved for Phase 2+ shared Python/TS packages
├── infrastructure/
│   ├── adrs/                   # Phase 1 ADR & specification conflict register
│   └── docker/                 # Dockerfiles + PostgreSQL least-privilege init SQL
├── scripts/                    # Non-destructive port check & verification scripts
├── tests/
│   └── integration/            # Live stack integration & contract verification tests
├── .github/workflows/          # GitHub Actions CI pipeline (no secrets)
├── documents/                  # Local-only 26 official specification PDFs (Git-ignored)
├── .env.example                # Safe configuration template (placeholders only)
├── docker-compose.yml          # 6-service local Compose stack (127.0.0.1 loopback)
└── pyproject.toml              # Shared Python Ruff lint/format & root pytest config
```

---

## Prerequisites

- Git
- Docker & Docker Compose
- Python 3.12 (`services/api` and `services/worker` each maintain isolated virtual environments)
- Node.js 24 & pnpm 11.17+

---

## Quick Start (Docker Compose)

### 1. Check Loopback Host Port Availability

Default loopback host bindings avoid common collisions on `5432`, `6379`, and `8000`:

| Service         | Container Port | Default Host Port (`127.0.0.1`) | Env Variable         |
| --------------- | -------------: | ------------------------------: | -------------------- |
| Web (`Next.js`) |         `3000` |                          `3000` | `WEB_HOST_PORT`      |
| API (`FastAPI`) |         `8000` |                          `8001` | `API_HOST_PORT`      |
| PostgreSQL      |         `5432` |                          `5435` | `POSTGRES_HOST_PORT` |
| Redis           |         `6379` |                          `6381` | `REDIS_HOST_PORT`    |

Verify ports before booting containers (Windows PowerShell):

```powershell
./scripts/check-ports.ps1
```

### 2. Create `.env` from `.env.example`

Never commit `.env` or place secrets in `NEXT_PUBLIC_*` variables. Copy `.env.example` to `.env` and replace every `REPLACE_WITH_*` value with strong locally generated secrets (keeping `POSTGRES_OWNER_PASSWORD`, `POSTGRES_APP_PASSWORD`, and `REDIS_PASSWORD` consistent inside `DATABASE_URL`, `MIGRATION_DATABASE_URL`, `REDIS_URL`, `CELERY_BROKER_URL`, and `CELERY_RESULT_BACKEND`):

```powershell
Copy-Item .env.example .env
```

Example secret generator:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### 3. Build and Start the 6-Service Stack

```powershell
docker compose up --build -d --wait
docker compose ps
```

### 4. Bootstrap the 9 PostgreSQL Schemas via Alembic

Run Alembic migrations in an isolated one-off `api` container supplying `.env` (which injects `MIGRATION_DATABASE_URL` for `nextrade_owner` DDL execution without exposing owner credentials inside the long-running `api` service):

```powershell
docker compose run --rm --no-deps --env-from-file .env api alembic upgrade head
docker compose run --rm --no-deps --env-from-file .env api alembic current
```

### 5. Verify Endpoints

- **Web Foundation UI:** `http://localhost:3000`
- **API Versioned Health (`NEX-DOC-009` envelope):** `http://localhost:8001/api/v1/health`
- **API Root Liveness/Readiness Probe:** `http://localhost:8001/health`
- **OpenAPI Docs (local/test only):** `http://localhost:8001/api/v1/docs`

Stop containers safely without deleting data volumes:

```powershell
docker compose stop
```

> **Safety Warning:** Never run `docker compose down -v` or `docker system prune --volumes` on active project environments, as doing so irreversibly deletes PostgreSQL and Redis volumes.

---

## Local Development & Verification

### Isolated Virtual Environments

- **API (`services/api/.venv`):**
  ```powershell
  python -m venv services/api/.venv
  ./services/api/.venv/Scripts/pip install -r services/api/requirements-dev.txt
  ```
- **Worker (`services/worker/.venv`):**
  ```powershell
  python -m venv services/worker/.venv
  ./services/worker/.venv/Scripts/pip install -r services/worker/requirements-dev.txt
  ```
- **Frontend (`apps/web/`):**
  ```powershell
  pnpm --dir apps/web install --frozen-lockfile
  ```

### Running Static Checks, Unit Tests & Builds

Run the full Phase 1 static & unit verification suite on Windows:

```powershell
./scripts/verify-foundation.ps1
```

Or execute component suites directly:

- **Lint & Format (Ruff):**
  - `services/api/.venv/Scripts/python -m ruff check services/api services/worker tests`
  - `services/api/.venv/Scripts/python -m ruff format --check services/api services/worker tests`
- **Typecheck (strict mypy):**
  - `services/api/.venv/Scripts/python -m mypy --config-file services/api/pyproject.toml services/api/app services/api/alembic/env.py services/api/tests`
  - `services/worker/.venv/Scripts/python -m mypy --config-file services/worker/pyproject.toml services/worker/worker_app services/worker/tests`
- **API Unit Tests (27 tests):** `Push-Location services/api; .\.venv\Scripts\python -m pytest -m unit; Pop-Location`
- **Worker Unit Tests (4 tests):** `Push-Location services/worker; .\.venv\Scripts\python -m pytest -m unit; Pop-Location`
- **Frontend Checks & Tests:**
  - `pnpm --dir apps/web peers check`
  - `pnpm --dir apps/web exec next typegen`
  - `pnpm --dir apps/web typecheck`
  - `pnpm --dir apps/web lint`
  - `pnpm --dir apps/web test`
  - `pnpm --dir apps/web build`
- **Playwright Smoke Test (against running stack):**
  - `pnpm --dir apps/web exec playwright install chromium`
  - `$env:EXPECT_HEALTHY_STACK='true'; $env:PLAYWRIGHT_BASE_URL='http://127.0.0.1:3000'; pnpm --dir apps/web test:e2e`

---

## CI Workflow

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) verifies repository hygiene (`documents/` and `.env` remain untracked, shell scripts use LF endings, Compose validates cleanly), Python Ruff/mypy/`pip-audit`/Pytest checks, Next.js peer/type/lint/Vitest/build checks, full 6-container Docker Compose startup with reversible `alembic upgrade head -> downgrade base -> upgrade head`, Redis outage `503` degradation & recovery, live Celery `ops.heartbeat` execution, and Playwright E2E smoke tests without storing secrets in workflow configuration.
