from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints import health as health_endpoint
from app.cache.redis import check_redis_health
from app.db.base import LOGICAL_SCHEMAS, Base
from app.db.session import DependencyStatus, check_database_health
from app.factory import create_app
from tests.conftest import make_test_settings


@pytest.mark.unit
def test_logical_schemas_and_naming_convention_match_docs() -> None:
    assert LOGICAL_SCHEMAS == (
        "core",
        "market",
        "fundamental",
        "analytics",
        "ml",
        "news",
        "portfolio",
        "engagement",
        "ops",
    )
    assert set(Base.metadata.naming_convention.keys()) == {"ix", "uq", "ck", "fk", "pk"}


@pytest.mark.unit
def test_health_endpoints_return_200_when_postgres_and_redis_are_healthy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_engine = MagicMock()
    fake_engine.dispose = AsyncMock()
    fake_redis = MagicMock()
    fake_redis.aclose = AsyncMock()

    monkeypatch.setattr("app.factory.create_db_engine", lambda _settings: fake_engine)
    monkeypatch.setattr("app.factory.create_session_factory", lambda _engine: MagicMock())
    monkeypatch.setattr("app.factory.create_redis_client", lambda _settings: fake_redis)
    monkeypatch.setattr(
        health_endpoint,
        "check_database_health",
        AsyncMock(return_value=DependencyStatus(status="healthy", latency_ms=1.4)),
    )
    monkeypatch.setattr(
        health_endpoint,
        "check_redis_health",
        AsyncMock(return_value=DependencyStatus(status="healthy", latency_ms=0.7)),
    )

    app = create_app(make_test_settings())
    with TestClient(app) as client:
        root_resp = client.get("/health", headers={"X-Request-ID": "health_req_01"})
        assert root_resp.status_code == 200
        root_data = root_resp.json()
        assert root_data["status"] == "healthy"
        assert root_data["checks"]["postgres"]["status"] == "healthy"
        assert root_data["checks"]["redis"]["status"] == "healthy"
        assert root_data["request_id"] == "health_req_01"

        v1_resp = client.get("/api/v1/health", headers={"X-Request-ID": "health_req_02"})
        assert v1_resp.status_code == 200
        v1_data = v1_resp.json()
        assert v1_data["data"]["status"] == "healthy"
        assert v1_data["data"]["service"] == "nextrade-api"
        assert v1_data["data"]["dependencies"]["postgres"]["status"] == "healthy"
        assert v1_data["data"]["dependencies"]["redis"]["status"] == "healthy"
        assert v1_data["meta"]["request_id"] == "health_req_02"
        assert v1_data["meta"]["api_version"] == "v1"

    fake_redis.aclose.assert_awaited_once()
    fake_engine.dispose.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.parametrize(
    ("db_ok", "redis_ok"),
    [
        (False, True),
        (True, False),
        (False, False),
    ],
)
def test_health_endpoints_return_503_when_any_dependency_unhealthy(
    monkeypatch: pytest.MonkeyPatch,
    db_ok: bool,
    redis_ok: bool,
) -> None:
    fake_engine = MagicMock()
    fake_engine.dispose = AsyncMock()
    fake_redis = MagicMock()
    fake_redis.aclose = AsyncMock()

    monkeypatch.setattr("app.factory.create_db_engine", lambda _settings: fake_engine)
    monkeypatch.setattr("app.factory.create_session_factory", lambda _engine: MagicMock())
    monkeypatch.setattr("app.factory.create_redis_client", lambda _settings: fake_redis)
    monkeypatch.setattr(
        health_endpoint,
        "check_database_health",
        AsyncMock(
            return_value=DependencyStatus(
                status="healthy" if db_ok else "unhealthy",
                latency_ms=1.1 if db_ok else None,
                detail=None if db_ok else "PostgreSQL connection unavailable.",
            )
        ),
    )
    monkeypatch.setattr(
        health_endpoint,
        "check_redis_health",
        AsyncMock(
            return_value=DependencyStatus(
                status="healthy" if redis_ok else "unhealthy",
                latency_ms=0.6 if redis_ok else None,
                detail=None if redis_ok else "Redis connection unavailable.",
            )
        ),
    )

    app = create_app(make_test_settings())
    with TestClient(app) as client:
        root_resp = client.get("/health")
        v1_resp = client.get("/api/v1/health")

    assert root_resp.status_code == 503
    assert root_resp.json()["status"] == "unhealthy"
    assert v1_resp.status_code == 503
    payload = v1_resp.json()
    assert payload["data"]["status"] == "unhealthy"
    assert payload["data"]["dependencies"]["postgres"]["status"] == (
        "healthy" if db_ok else "unhealthy"
    )
    assert payload["data"]["dependencies"]["redis"]["status"] == (
        "healthy" if redis_ok else "unhealthy"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_dependency_health_checkers_never_fake_healthy() -> None:
    db_none = await check_database_health(None)
    assert db_none.status == "unhealthy"

    redis_none = await check_redis_health(None)
    assert redis_none.status == "unhealthy"

    broken_redis = MagicMock()
    broken_redis.ping = AsyncMock(side_effect=ConnectionError("refused"))
    redis_err = await check_redis_health(broken_redis)
    assert redis_err.status == "unhealthy"

    false_redis = MagicMock()
    false_redis.ping = AsyncMock(return_value=False)
    redis_false = await check_redis_health(false_redis)
    assert redis_false.status == "unhealthy"

    broken_engine = MagicMock()
    broken_engine.connect.side_effect = OSError("db unreachable")
    db_err = await check_database_health(broken_engine)
    assert db_err.status == "unhealthy"
