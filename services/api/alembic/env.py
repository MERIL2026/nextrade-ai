from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.core.config import get_settings
from app.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _resolve_migration_url() -> str:
    """Resolve authoritative owner migration URL without exposing credentials in alembic.ini."""
    configured = config.get_main_option("sqlalchemy.url")
    if configured:
        return configured

    direct_migration_url = os.environ.get("MIGRATION_DATABASE_URL", "").strip()
    if direct_migration_url:
        if direct_migration_url.startswith("postgresql://"):
            return direct_migration_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return direct_migration_url

    return get_settings().sqlalchemy_migration_uri


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = _resolve_migration_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        include_schemas=True,
        compare_type=True,
        compare_server_default=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode using the schema-owner PostgreSQL connection."""
    url = _resolve_migration_url()
    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
