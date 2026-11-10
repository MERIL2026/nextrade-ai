# Operations & Developer Scripts (`scripts/`)

Developer helper scripts and safe operational checks live here.

> **Safety rules (`NEX-DOC-011`, `NEX-DOC-022`):**
> - Never store passwords, tokens, API keys, or production connection strings in scripts.
> - Scripts must never run destructive Docker (`down -v`, `system prune --volumes`) or database reset commands automatically.

