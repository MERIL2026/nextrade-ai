# Shared Packages (`packages/`)

Reserved for cross-service shared contracts, schemas, and domain primitives as NEXTRADE AI progresses from Phase 1 into Phase 2+.

Planned subdirectories (to be populated cleanly as modules graduate):
- `shared-types/`: OpenAPI-derived TypeScript types and API response contracts (`NEX-DOC-009`, `NEX-DOC-011`).
- `domain/` / `quant/` / `data/` / `ml/` / `rag/`: Modular Python domain libraries when shared across `services/api` and `services/worker` (`NEX-DOC-025`).

> **Phase 1 rule:** Keep packages minimal and avoid speculative abstractions before concrete Phase 2 data models and ingestion contracts exist.

