from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints.health import RootHealthProbeSchema, root_health_probe
from app.api.v1.router import api_v1_router
from app.cache.redis import create_redis_client
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.security import RequestContextMiddleware
from app.db.session import create_db_engine, create_session_factory

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Construct and configure the NEXTRADE AI FastAPI modular monolith application."""
    resolved_settings = settings or get_settings()

    configure_logging(
        service=resolved_settings.service_name,
        environment=resolved_settings.app_env,
        level=resolved_settings.log_level,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = resolved_settings
        app.state.db_engine = create_db_engine(resolved_settings)
        app.state.db_sessionmaker = create_session_factory(app.state.db_engine)
        app.state.redis = create_redis_client(resolved_settings)

        logger.info(
            "API lifecycle startup completed",
            extra={
                "app_env": resolved_settings.app_env,
                "api_prefix": resolved_settings.api_prefix,
                "docs_enabled": resolved_settings.docs_enabled,
            },
        )
        try:
            yield
        finally:
            logger.info("API lifecycle shutdown initiated")
            redis_client = getattr(app.state, "redis", None)
            if redis_client is not None:
                await redis_client.aclose()
            db_engine = getattr(app.state, "db_engine", None)
            if db_engine is not None:
                await db_engine.dispose()
            logger.info("API lifecycle shutdown completed")

    docs_url = f"{resolved_settings.api_prefix}/docs" if resolved_settings.docs_enabled else None
    redoc_url = f"{resolved_settings.api_prefix}/redoc" if resolved_settings.docs_enabled else None
    openapi_url = (
        f"{resolved_settings.api_prefix}/openapi.json" if resolved_settings.docs_enabled else None
    )

    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        debug=resolved_settings.debug,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings

    # Middleware order: Starlette wraps LIFO, so adding CORSMiddleware first and
    # RequestContextMiddleware second makes RequestContextMiddleware outermost.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Accept",
            "X-Request-ID",
            "X-Correlation-ID",
            "Idempotency-Key",
            "X-CSRF-Token",
        ],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(RequestContextMiddleware)

    register_exception_handlers(app)

    app.add_api_route(
        "/health",
        root_health_probe,
        methods=["GET"],
        response_model=RootHealthProbeSchema,
        tags=["Operations"],
        summary="Root readiness probe",
        responses={
            200: {"description": "Service and dependencies are healthy."},
            503: {"description": "Service or dependencies are unavailable."},
        },
    )
    app.include_router(api_v1_router, prefix=resolved_settings.api_prefix)

    return app
