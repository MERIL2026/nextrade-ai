# Modular Monolith Domain Boundaries (`app/modules/`)

Per `NEX-DOC-006` §6 (*Backend Module Boundaries*), Phase 2+ domain packages will be added as clearly separated modules here without introducing premature microservices:

- `identity`: users, roles, sessions, entitlements
- `instruments`: exchanges, canonical instruments, aliases, sectors, trading calendars
- `market_data`: provider adapters, price bars, daily snapshots, corporate actions
- `fundamentals`: financial periods, normalized observations, metric definitions
- `analytics`: deterministic indicators, valuations, risk metrics
- `scanner`: filter schemas and scheduled scans
- `signals`: rule-based/calibrated research evidence
- `portfolio`: virtual portfolios, append-only transaction ledger, holdings
- `news`: licensed articles, entity links, metadata
- `assistant`: grounded RAG retrieval and citation validation
- `notifications`: user watchlists, alerts, notifications
- `operations`: job records, data-quality checks, audit logs

> **Phase 1 boundary:** No domain tables, stock predictions, paid feeds, or live broker execution exist in Phase 1.

