# ADR-0001: Phase 1 Engineering Foundation Decisions

| Field | Value |
|---|---|
| **ADR ID / Title** | ADR-0001 — Phase 1 Monorepo, Compose Port Isolation, Health & Schema Bootstrap |
| **Date** | 2026-11-10 |
| **Status** | Accepted (Phase 1 Baseline) |
| **Owner** | Architecture & Platform Engineering |

## Context

The 26 official NEXTRADE AI specifications (`NEX-DOC-001` through `NEX-DOC-026`) describe several slightly varying monorepo layouts, Compose topologies, health paths, and PostgreSQL bootstrap boundaries. In addition, the local development host already runs unrelated containers/processes bound to ports `5432`, `6379`, and `8000`.

## Decision

1. **Monorepo layout (Option A)**:
   - Use `apps/web/`, `services/api/`, `services/worker/`, `packages/`, `infrastructure/docker/`, `infrastructure/adrs/`, `scripts/`, `tests/`, `.github/workflows/`, root `pyproject.toml`, `docker-compose.yml`, and `README.md`.
   - Keep `documents/` (26 `v1.0` PDFs) untouched locally and excluded from Git.
2. **Docker Compose & non-colliding host ports**:
   - Define 6 services: `postgres`, `redis`, `api`, `worker`, `scheduler`, and `web`.
   - Keep standard internal container ports (`postgres:5432`, `redis:6379`, `api:8000`, `web:3000`).
   - Bind loopback (`127.0.0.1`) configurable host ports defaulting to `WEB_HOST_PORT=3000`, `API_HOST_PORT=8001`, `POSTGRES_HOST_PORT=5435`, and `REDIS_HOST_PORT=6381` to avoid colliding with active host services.
3. **Database migration scope**:
   - Configure SQLAlchemy 2 + Alembic in `services/api/`.
   - Create an initial bootstrap migration establishing the 9 documented PostgreSQL schemas (`core`, `market`, `fundamental`, `analytics`, `ml`, `news`, `portfolio`, `engagement`, `ops`) with least-privilege runtime role separation (`nextrade_owner` vs non-superuser `nextrade_app`), deferring Phase 2 domain tables.
4. **Health endpoints**:
   - Expose both `GET /health` (lightweight liveness/readiness probe returning HTTP `200`/`503`) and `GET /api/v1/health` (returning the `NEX-DOC-009` `{data, meta}` envelope with real PostgreSQL `SELECT 1` and Redis `PING` checks).
5. **Frontend testing**:
   - Configure Vitest + React Testing Library for unit/component tests and Playwright for browser E2E smoke tests (`NEX-DOC-017` §10.3).

## Consequences

- Reconciles `NEX-DOC-006`, `007`, `009`, `011`, `017`, `020`, `025`, and `026` cleanly without disrupting existing local services.
- Keeps Phase 1 strictly free of Phase 2+ schemas, fabricated market data, live trading, ML models, or paid market-data providers.

## Security & Data Rights

- No credentials committed; `.env.example` holds `REPLACE_WITH_*` placeholders only.
- Settings validation fails closed outside `local`/`test` when required secrets or allowed CORS origins are missing/placeholder.
- Runtime containers run as dedicated non-root users with Redis authentication enabled and loopback-only local host bindings.

