from __future__ import annotations

import asyncio
import logging
import time

from fastapi import Request
from redis.asyncio import Redis

from app.core.config import Settings
from app.db.session import DependencyStatus

logger = logging.getLogger(__name__)


def create_redis_client(settings: Settings) -> Redis:
    """Create bounded async Redis client for cache and coordination only."""
    return Redis.from_url(
        settings.redis_url.get_secret_value(),
        socket_connect_timeout=settings.health_check_timeout_seconds,
        socket_timeout=settings.health_check_timeout_seconds,
        decode_responses=True,
    )


async def get_redis_client(request: Request) -> Redis:
    """FastAPI dependency returning initialized async Redis client."""
    client: Redis = request.app.state.redis
    return client


async def check_redis_health(
    client: Redis | None,
    *,
    timeout_seconds: float = 2.5,
) -> DependencyStatus:
    """Verify live Redis connectivity via PING; never fake healthy."""
    if client is None:
        return DependencyStatus(
            status="unhealthy",
            detail="Redis client is not initialized.",
        )

    started = time.perf_counter()
    try:
        pong = await asyncio.wait_for(client.ping(), timeout=timeout_seconds)
        if not pong:
            return DependencyStatus(
                status="unhealthy",
                detail="Redis PING did not succeed.",
            )
        latency_ms = round((time.perf_counter() - started) * 1000.0, 2)
        return DependencyStatus(status="healthy", latency_ms=latency_ms)
    except TimeoutError:
        logger.warning("Redis health check timed out")
        return DependencyStatus(
            status="unhealthy",
            detail="Redis connectivity check timed out.",
        )
    except Exception:
        logger.warning("Redis health check failed", exc_info=True)
        return DependencyStatus(
            status="unhealthy",
            detail="Redis connection unavailable.",
        )
