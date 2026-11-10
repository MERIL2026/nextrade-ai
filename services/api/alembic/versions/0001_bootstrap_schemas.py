"""Bootstrap the nine NEXTRADE AI logical PostgreSQL schemas.

Revision ID: 0001_bootstrap_schemas
Revises:
Create Date: 2026-11-10 00:00:00+00:00
"""

from __future__ import annotations

import os
import re
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.db.base import LOGICAL_SCHEMAS

# revision identifiers, used by Alembic.
revision: str = "0001_bootstrap_schemas"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ROLE_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")


def _get_app_role_name() -> str:
    candidate = os.environ.get("POSTGRES_APP_USER", "nextrade_app").strip() or "nextrade_app"
    if not _ROLE_NAME_PATTERN.fullmatch(candidate):
        raise ValueError(f"Unsafe POSTGRES_APP_USER identifier: {candidate!r}")
    return candidate


def upgrade() -> None:
    app_role = _get_app_role_name()
    conn = op.get_bind()

    for schema_name in LOGICAL_SCHEMAS:
        conn.execute(
            sa.text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}" AUTHORIZATION CURRENT_USER')
        )

    role_exists = (
        conn.execute(
            sa.text("SELECT 1 FROM pg_roles WHERE rolname = :role_name"),
            {"role_name": app_role},
        ).scalar()
        is not None
    )
    if role_exists:
        for schema_name in LOGICAL_SCHEMAS:
            conn.execute(sa.text(f'GRANT USAGE ON SCHEMA "{schema_name}" TO "{app_role}"'))


def downgrade() -> None:
    app_role = _get_app_role_name()
    conn = op.get_bind()

    role_exists = (
        conn.execute(
            sa.text("SELECT 1 FROM pg_roles WHERE rolname = :role_name"),
            {"role_name": app_role},
        ).scalar()
        is not None
    )
    if role_exists:
        for schema_name in reversed(LOGICAL_SCHEMAS):
            schema_exists = (
                conn.execute(
                    sa.text("SELECT 1 FROM pg_namespace WHERE nspname = :schema_name"),
                    {"schema_name": schema_name},
                ).scalar()
                is not None
            )
            if schema_exists:
                conn.execute(sa.text(f'REVOKE USAGE ON SCHEMA "{schema_name}" FROM "{app_role}"'))

    # Drop in reverse order WITHOUT CASCADE so non-empty schemas fail safely rather than dropping data.
    for schema_name in reversed(LOGICAL_SCHEMAS):
        conn.execute(sa.text(f'DROP SCHEMA IF EXISTS "{schema_name}" RESTRICT'))
