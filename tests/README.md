# Repository-Level Tests (`tests/`)

Cross-service integration and end-to-end smoke checks reside here, complementing:
- `services/api/tests/`: FastAPI unit, config, logging, middleware, and API health tests.
- `services/worker/tests/`: Celery app, configuration, and task wiring unit tests.
- `apps/web/`: Frontend Vitest + React Testing Library unit/component tests and Playwright E2E/smoke tests.

See `NEX-DOC-017` (*Testing & Quality Assurance Plan*) for the platform test pyramid and evidence standards.

