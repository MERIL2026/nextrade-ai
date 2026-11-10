from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.exceptions import AppError
from app.factory import create_app
from tests.conftest import make_test_settings


class _DemoBody(BaseModel):
    symbol: str
    limit: int


@pytest.mark.unit
def test_request_id_and_security_headers_are_returned() -> None:
    app = create_app(make_test_settings())
    client = TestClient(app)

    response = client.get("/api/v1/does-not-exist", headers={"X-Request-ID": "trace_abc_12345"})
    assert response.status_code == 404
    assert response.headers["X-Request-ID"] == "trace_abc_12345"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Cache-Control"] == "no-store"

    body = response.json()
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["meta"]["request_id"] == "trace_abc_12345"
    assert body["meta"]["api_version"] == "v1"


@pytest.mark.unit
def test_invalid_request_id_header_is_replaced() -> None:
    app = create_app(make_test_settings())
    client = TestClient(app)

    response = client.get("/api/v1/missing", headers={"X-Request-ID": "bad id with spaces!"})
    assert response.status_code == 404
    generated = response.headers["X-Request-ID"]
    assert generated.startswith("req_")
    assert response.json()["meta"]["request_id"] == generated


@pytest.mark.unit
def test_validation_error_uses_standard_envelope() -> None:
    app = create_app(make_test_settings())

    @app.post("/api/v1/_test/validate")
    async def _validate(payload: _DemoBody) -> dict[str, object]:
        return {"symbol": payload.symbol, "limit": payload.limit}

    client = TestClient(app)
    response = client.post("/api/v1/_test/validate", json={"symbol": "INFY"})
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"][0]["field"] == "limit"
    assert body["meta"]["api_version"] == "v1"


@pytest.mark.unit
def test_app_error_and_unhandled_exception_never_leak_secrets() -> None:
    app = create_app(make_test_settings())

    @app.get("/api/v1/_test/app-error")
    async def _app_error() -> dict[str, str]:
        raise AppError(status_code=400, code="INVALID_FILTER", message="Invalid filter syntax.")

    @app.get("/api/v1/_test/boom")
    async def _boom() -> dict[str, str]:
        raise RuntimeError("postgresql+psycopg://user:super_secret_pw@db:5432/nextrade failed")

    client = TestClient(app, raise_server_exceptions=False)

    app_err_resp = client.get("/api/v1/_test/app-error")
    assert app_err_resp.status_code == 400
    assert app_err_resp.json()["error"]["code"] == "INVALID_FILTER"

    boom_resp = client.get("/api/v1/_test/boom", headers={"X-Request-ID": "req_boom_1234"})
    assert boom_resp.status_code == 500
    boom_json = boom_resp.json()
    assert boom_json["error"]["code"] == "INTERNAL_ERROR"
    assert "super_secret_pw" not in boom_resp.text
    assert "RuntimeError" not in boom_resp.text
    assert boom_resp.headers["X-Request-ID"] == "req_boom_1234"
    assert boom_resp.headers["X-Content-Type-Options"] == "nosniff"
    assert boom_resp.headers["Cache-Control"] == "no-store"


@pytest.mark.unit
def test_cors_enforces_explicit_allowlist_and_hides_docs_in_production() -> None:
    prod_settings = make_test_settings(
        app_env="production",
        app_secret="P" * 48,
        cors_origins=["https://app.nextrade.example"],
    )
    app = create_app(prod_settings)
    client = TestClient(app)

    allowed = client.options(
        "/api/v1/health",
        headers={
            "Origin": "https://app.nextrade.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert allowed.status_code == 200
    assert allowed.headers.get("access-control-allow-origin") == "https://app.nextrade.example"

    blocked = client.options(
        "/api/v1/health",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in blocked.headers

    docs_resp = client.get("/api/v1/docs")
    assert docs_resp.status_code == 404
    openapi_resp = client.get("/api/v1/openapi.json")
    assert openapi_resp.status_code == 404
