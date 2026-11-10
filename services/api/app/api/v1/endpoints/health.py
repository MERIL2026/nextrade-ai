from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.cache.redis import check_redis_health
from app.core.config import Settings
from app.core.schemas import ResponseMeta, SuccessResponse
from app.db.session import DependencyStatus, check_database_health

router = APIRouter(tags=["Operations"])


class DependencyHealthSchema(BaseModel):
    """Serializable health state for a single backing service."""

    status: Literal["healthy", "unhealthy"]
    latency_ms: float | None = None
    detail: str | None = None


class DependenciesReportSchema(BaseModel):
    """Connectivity report for authoritative database and ephemeral cache/broker."""

    postgres: DependencyHealthSchema
    redis: DependencyHealthSchema


class HealthPayloadSchema(BaseModel):
    """Health status payload returned under /api/v1/health."""

    status: Literal["healthy", "unhealthy"]
    service: str
    environment: str
    version: str
    dependencies: DependenciesReportSchema


class RootHealthProbeSchema(BaseModel):
    """Lightweight container/load-balancer readiness payload returned under /health."""

    status: Literal["healthy", "unhealthy"]
    service: str
    environment: str
    checks: DependenciesReportSchema
    as_of: datetime
    request_id: str


def _to_schema(dep: DependencyStatus) -> DependencyHealthSchema:
    return DependencyHealthSchema(
        status="healthy" if dep.status == "healthy" else "unhealthy",
        latency_ms=dep.latency_ms,
        detail=dep.detail,
    )


async def evaluate_system_health(request: Request) -> tuple[bool, DependenciesReportSchema]:
    """Run live checks against PostgreSQL and Redis with configured timeout."""
    settings: Settings = request.app.state.settings
    timeout = settings.health_check_timeout_seconds
    db_status = await check_database_health(
        getattr(request.app.state, "db_engine", None),
        timeout_seconds=timeout,
    )
    redis_status = await check_redis_health(
        getattr(request.app.state, "redis", None),
        timeout_seconds=timeout,
    )
    is_healthy = db_status.status == "healthy" and redis_status.status == "healthy"
    report = DependenciesReportSchema(
        postgres=_to_schema(db_status),
        redis=_to_schema(redis_status),
    )
    return is_healthy, report


async def root_health_probe(request: Request) -> JSONResponse:
    """Handle GET /health container/infrastructure health checks."""
    settings: Settings = request.app.state.settings
    is_healthy, report = await evaluate_system_health(request)
    request_id = getattr(request.state, "request_id", "req_unknown")
    payload = RootHealthProbeSchema(
        status="healthy" if is_healthy else "unhealthy",
        service=settings.service_name,
        environment=settings.app_env,
        checks=report,
        as_of=datetime.now(UTC),
        request_id=request_id,
    )
    return JSONResponse(
        status_code=(status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE),
        content=payload.model_dump(mode="json"),
    )


@router.get(
    "/health",
    response_model=SuccessResponse[HealthPayloadSchema],
    summary="Check API and backing dependency health",
    responses={
        200: {"description": "API and all required dependencies are healthy."},
        503: {"description": "One or more required dependencies are unavailable."},
    },
)
async def versioned_health_check(request: Request) -> JSONResponse:
    """Return NEX-DOC-009 envelope reporting real PostgreSQL and Redis health."""
    settings: Settings = request.app.state.settings
    is_healthy, report = await evaluate_system_health(request)
    request_id = getattr(request.state, "request_id", "req_unknown")

    envelope = SuccessResponse[HealthPayloadSchema](
        data=HealthPayloadSchema(
            status="healthy" if is_healthy else "unhealthy",
            service=settings.service_name,
            environment=settings.app_env,
            version=settings.app_version,
            dependencies=report,
        ),
        meta=ResponseMeta(
            request_id=request_id,
            api_version="v1",
            as_of=datetime.now(UTC),
        ),
    )
    return JSONResponse(
        status_code=(status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE),
        content=envelope.model_dump(mode="json"),
    )
