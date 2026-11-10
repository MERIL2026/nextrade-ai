from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DependencyStatus:
    """Result of an individual infrastructure dependency probe."""

    status: str
    latency_ms: float | None = None
    detail: str | None = None


def create_db_engine(settings: Settings) -> AsyncEngine:
    """Create bounded SQLAlchemy 2 async engine using psycopg."""
    connect_timeout = max(1, round(settings.health_check_timeout_seconds))
    return create_async_engine(
        settings.sqlalchemy_database_uri,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout_seconds,
        connect_args={"connect_timeout": connect_timeout},
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create async session factory with safe defaults."""
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield an async database session scoped to a request."""
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.db_sessionmaker
    async with session_factory() as session:
        yield session


async def check_database_health(
    engine: AsyncEngine | None,
    *,
    timeout_seconds: float = 2.5,
) -> DependencyStatus:
    """Verify live PostgreSQL connectivity with SELECT 1; never fake healthy."""
    if engine is None:
        return DependencyStatus(
            status="unhealthy",
            detail="Database engine is not initialized.",
        )

    started = time.perf_counter()
    try:

        async def _probe() -> None:
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                row = result.scalar_one()
                if row != 1:
                    raise RuntimeError("Unexpected PostgreSQL health query result.")

        await asyncio.wait_for(_probe(), timeout=timeout_seconds)
        latency_ms = round((time.perf_counter() - started) * 1000.0, 2)
        return DependencyStatus(status="healthy", latency_ms=latency_ms)
    except TimeoutError:
        logger.warning("PostgreSQL health check timed out")
        return DependencyStatus(
            status="unhealthy",
            detail="PostgreSQL connectivity check timed out.",
        )
    except Exception:
        logger.warning("PostgreSQL health check failed", exc_info=True)
        return DependencyStatus(
            status="unhealthy",
            detail="PostgreSQL connection unavailable.",
        )
