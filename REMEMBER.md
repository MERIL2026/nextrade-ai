# NEXTRADE AI — Engineering Memory & Phase 1 Handoff (`REMEMBER.md`)

**Last Updated:** 2026-11-10
**Repository:** `https://github.com/MERIL2026/nextrade-ai.git` (`main`)
**Current Milestone:** Phase 1 Engineering Foundation — Complete & Audited (Ready for Phase 1 GitHub Backup; Phase 2 Not Started)

---

## 1. Product Guardrails & Non-Negotiables

- **Target Markets:** Indian (**NSE**, **BSE**) and US (**NYSE**, **NASDAQ**) financial intelligence and equity research.
- **Compliance Boundary:** Research, analytics, and decision-support only. Never implement automatic live trade execution and never promise guaranteed financial returns or investment certainty.
- **Local Documentation Privacy:** `documents/` holds the 26 authoritative specification PDFs (`NEX-DOC-001` through `NEX-DOC-026`) and **must stay local and excluded from Git** (`.gitignore` `/documents/`). Never delete, move, rename, or upload any PDF.
- **No Phase 2 Premature Work:** Phase 1 establishes the monorepo, runtime containers, health telemetry, role-separated 9-schema DB bootstrap, worker skeleton, test harnesses, and CI. No domain business tables, synthetic market prices, predictive ML models, or paid market-data providers exist yet.

---

## 2. Architecture Summary Delivered in Phase 1

- **Layout (Option A Modular Monolith):**
  - `apps/web/` — Next.js `16.4.6`, React `19.3.1`, TypeScript `6.0.3` (strict), Tailwind CSS `4.3.5`, Vitest `5.1.0` + React Testing Library `16.3.3`, Playwright `1.65.0`. Queries FastAPI `/api/v1/health` via SSR (`INTERNAL_API_BASE_URL`) and browser probes (`NEXT_PUBLIC_API_BASE_URL`).
  - `services/api/` — Python `3.12` modular monolith using FastAPI, Pydantic v2 (`pydantic-settings` fail-closed outside `local`/`test`), SQLAlchemy 2 async (`psycopg`), Alembic, secret-redacting UTC JSON logging, `X-Request-ID` tracing, security headers, strict CORS allowlists, `GET /health`, and `GET /api/v1/health` (`NEX-DOC-009` `{data, meta}` envelope with real PostgreSQL `SELECT 1` and Redis `PING` checks).
  - `services/worker/` — Celery 5 worker and Beat scheduler backed by authenticated Redis with idempotent `ops.heartbeat` task skeleton.
  - `packages/` — Reserved for Phase 2+ shared Python/TypeScript libraries.
  - `infrastructure/` — Multi-stage non-root Dockerfiles (UID `10001`), PostgreSQL role initialization SQL (`infrastructure/docker/postgres/init/01-init-roles.sh`, pure LF), `ADR-0001`, and `CONFLICT_REGISTER.md`.
  - `scripts/` — Non-destructive port check (`scripts/check-ports.ps1`) and static/unit verification suite (`scripts/verify-foundation.ps1`).
  - `tests/integration/` — Live full-stack integration suite (`test_foundation_integration.py`).
  - `.github/workflows/ci.yml` — Secret-free CI pipeline covering repo hygiene, Python Ruff/mypy/`pip-audit`/Pytest, frontend peer/typegen/TS/ESLint/Vitest/build, full 6-service Compose integration, Alembic reversibility, Redis outage `503` degradation/recovery, Celery task verification, and Playwright smoke tests.

### Docker Compose Topology (`name: nextrade-ai`)

| Service | Internal Port | Loopback Host Binding (`127.0.0.1`) | Runtime Role / Notes |
| --- | --- | --- | --- |
| `postgres` | `5432` | `POSTGRES_HOST_PORT` (default `5435`) | `postgres:18.6-alpine`; schema owner `nextrade_owner` vs runtime `nextrade_app` |
| `redis` | `6379` | `REDIS_HOST_PORT` (default `6381`) | `redis:8.0-alpine`; `--requirepass` + AOF enabled |
| `api` | `8000` | `API_HOST_PORT` (default `8001`) | Non-root `10001`; receives `DATABASE_URL` (`nextrade_app`), not `MIGRATION_DATABASE_URL` |
| `worker` | — | None | Non-root `10001`; Celery worker polling Redis broker |
| `scheduler` | — | None | Non-root `10001`; Celery Beat (`--schedule=/tmp/celerybeat-schedule`) |
| `web` | `3000` | `WEB_HOST_PORT` (default `3000`) | Non-root `10001`; Next.js standalone server |

### PostgreSQL Schema Bootstrap (`0001_bootstrap_schemas`)

Creates and grants least-privilege `USAGE` (no `CREATE` for `nextrade_app`, `public` `CREATE` revoked) across the 9 logical schemas from `NEX-DOC-007` §3.1:

`core`, `market`, `fundamental`, `analytics`, `ml`, `news`, `portfolio`, `engagement`, `ops`

---

## 3. Work Completed & Verified Today (2026-11-10)

1. **Full 26-Document Audit & Governance Setup:** Reviewed `NEX-DOC-001` through `NEX-DOC-026`, documented resolved Phase 1 choices in `infrastructure/adrs/ADR-0001-phase1-foundation-decisions.md`, and logged open future-phase specification variances (`CONF-001` through `CONF-008`) in `infrastructure/adrs/CONFLICT_REGISTER.md`.
2. **Git & Secret Hygiene Configured:** Added comprehensive `.gitignore` (excluding `/documents/`, `.env`, `.env.*` while preserving `!.env.example`, venvs, caches, build artifacts, secrets, keys/certs) and `.gitattributes` enforcing LF endings on Linux scripts, source code, Markdown, and configs. Fixed unanchored `/lib/` pattern so `apps/web/src/lib/` tracks cleanly.
3. **Static & Unit Verification Passed:**
   - Ruff check + format check across `services/api`, `services/worker`, and `tests`.
   - Strict `mypy` across API and Worker source/tests.
   - `pip-audit` against pinned `requirements.txt` manifests.
   - API Pytest unit suite (`27` tests passed) and Worker Pytest unit suite (`4` tests passed).
   - Frontend `pnpm peers check`, `next typegen`, `tsc --noEmit`, ESLint, Vitest + RTL (`8` tests passed), and production `next build`.
4. **Live Container & Integration Verification Passed (via isolated verification run):**
   - Verified all 6 containers healthy (`127.0.0.1` ports), non-root UID `10001`, absence of `MIGRATION_DATABASE_URL` inside running `api` container.
   - Verified reversible Alembic migration cycle (`upgrade head` -> `downgrade base` -> `upgrade head`) using `--env-from-file .env`.
   - Passed live integration suite (`4` tests: API health/headers/CORS, 9 schemas + least-privilege `nextrade_app`, Redis auth enforcement, Web SSR render).
   - Verified live Celery `ops.heartbeat` task execution, Redis outage `503` readiness degradation + automatic `200` recovery on restart, and Playwright Chromium E2E smoke test.
5. **Read-Only Final Acceptance Audit Completed:** Confirmed all 26 PDFs unchanged, zero tracked secrets or `.env` on disk, pre-existing local Docker workloads untouched, updated `README.md` local commands (`next typegen` + `ruff format --check`), and prepared staged Phase 1 files for safe GitHub backup.

---

## 4. Known Operational State & Pending Gates

- **Docker Host Note:** Pre-existing non-NEXTRADE Docker containers and volumes on the workstation remain running and untouched. Six **stopped** `nextrade-verify-*` containers, two verification volumes (`nextrade-verify_postgres_data`, `nextrade-verify_redis_data`), one bridge network (`nextrade-verify_nextrade_internal`), and four Phase 1 build images remain on disk from earlier verification and were intentionally left untouched. Never run `docker system prune --volumes` or `docker compose down -v`.
- **`.env` File State:** `.env` is intentionally absent from the repo working tree. Before booting the normal `nextrade-ai` Compose stack, copy `.env.example` to `.env` and populate fresh random secrets.
- **Open `NEX-DOC-026` Closeout Gates Pending Push:**
  - **G1.1:** Fresh-clone clean startup verification once pushed to GitHub.
  - **G1.2:** GitHub Actions CI run passing remotely + `main` branch protection rules enabled on GitHub.

---

## 5. Exact Commands to Resume Tomorrow

### Boot & Migrate Normal `nextrade-ai` Stack
```powershell
./scripts/check-ports.ps1
Copy-Item .env.example .env   # then replace all placeholder secrets with fresh random tokens
docker compose up --build -d --wait
docker compose run --rm --no-deps --env-from-file .env api alembic upgrade head
docker compose run --rm --no-deps --env-from-file .env api alembic current
docker compose ps
```

### Safe Shutdown (Preserves Volumes)
```powershell
docker compose stop
```

### Run Full Local Static & Unit Verification
```powershell
./scripts/verify-foundation.ps1
```

---

## 6. Next Milestone: Phase 2 Readiness Checklist (Not Started)

Before writing Phase 2 domain tables, authentication, and market ingestion services:
1. Resolve open Phase 2+ decisions in `infrastructure/adrs/CONFLICT_REGISTER.md` with owners (`CONF-002` API path alignment, `CONF-003` cookie session vs managed auth, `CONF-004` `CITEXT`/partitioning/`fx_rates`/NAV schema details, `CONF-005` market-data provider licensing).
2. Confirm GitHub Actions CI (`.github/workflows/ci.yml`) succeeds on `main` and configure branch protection.
3. Begin Phase 2 incremental Alembic revisions on top of `0001_bootstrap_schemas`.
