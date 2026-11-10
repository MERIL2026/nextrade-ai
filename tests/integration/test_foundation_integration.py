from __future__ import annotations

import os

import httpx
import psycopg
import pytest
import redis

EXPECTED_LOGICAL_SCHEMAS = (
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


def _require_live_integration() -> None:
    if os.environ.get("NEXTRADE_RUN_LIVE_INTEGRATION") != "1":
        pytest.skip("Set NEXTRADE_RUN_LIVE_INTEGRATION=1 to execute live stack integration tests.")


@pytest.mark.integration
def test_live_api_health_v1_envelope_cors_and_headers() -> None:
    """Verify live FastAPI /health, /api/v1/health envelope, security headers, and CORS."""
    _require_live_integration()
    api_base = os.environ.get("INTEGRATION_API_BASE_URL", "http://127.0.0.1:8001").rstrip("/")

    with httpx.Client(base_url=api_base, timeout=5.0) as client:
        root_resp = client.get("/health", headers={"X-Request-ID": "int_root_health_01"})
        assert root_resp.status_code == 200
        assert root_resp.headers.get("x-request-id") == "int_root_health_01"
        assert root_resp.headers.get("x-content-type-options") == "nosniff"
        assert root_resp.headers.get("x-frame-options") == "DENY"
        assert root_resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
        assert root_resp.headers.get("cache-control") == "no-store"

        root_payload = root_resp.json()
        assert root_payload["status"] == "healthy"
        assert root_payload["checks"]["postgres"]["status"] == "healthy"
        assert root_payload["checks"]["redis"]["status"] == "healthy"
        assert root_payload["request_id"] == "int_root_health_01"

        v1_resp = client.get("/api/v1/health", headers={"X-Request-ID": "int_v1_health_01"})
        assert v1_resp.status_code == 200
        assert v1_resp.headers.get("cache-control") == "no-store"
        v1_payload = v1_resp.json()
        assert v1_payload["data"]["status"] == "healthy"
        assert v1_payload["data"]["dependencies"]["postgres"]["status"] == "healthy"
        assert v1_payload["data"]["dependencies"]["redis"]["status"] == "healthy"
        assert v1_payload["meta"]["api_version"] == "v1"
        assert v1_payload["meta"]["request_id"] == "int_v1_health_01"

        allowed_preflight = client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert allowed_preflight.status_code == 200
        assert (
            allowed_preflight.headers.get("access-control-allow-origin") == "http://localhost:3000"
        )

        blocked_preflight = client.options(
            "/api/v1/health",
            headers={
                "Origin": "https://untrusted.example",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "access-control-allow-origin" not in blocked_preflight.headers


@pytest.mark.integration
def test_live_postgres_nine_schemas_and_least_privilege_role() -> None:
    """Verify the 9 Alembic bootstrap schemas and non-superuser runtime role privileges."""
    _require_live_integration()
    dsn = os.environ.get("INTEGRATION_POSTGRES_DSN", "").strip()
    if not dsn:
        pytest.fail("INTEGRATION_POSTGRES_DSN must be set when NEXTRADE_RUN_LIVE_INTEGRATION=1.")

    normalized_dsn = (
        dsn.replace("postgresql+psycopg://", "postgresql://", 1)
        if dsn.startswith("postgresql+psycopg://")
        else dsn
    )
    app_user = os.environ.get("POSTGRES_APP_USER", "nextrade_app")

    with psycopg.connect(normalized_dsn, connect_timeout=5) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name = ANY(%s)
            """,
            (list(EXPECTED_LOGICAL_SCHEMAS),),
        )
        present_schemas = {row[0] for row in cur.fetchall()}
        assert present_schemas == set(EXPECTED_LOGICAL_SCHEMAS)

        cur.execute(
            """
            SELECT rolsuper, rolcreatedb, rolcreaterole, rolbypassrls, rolcanlogin
            FROM pg_roles
            WHERE rolname = %s
            """,
            (app_user,),
        )
        role_flags = cur.fetchone()
        assert role_flags is not None, f"Expected role {app_user!r} to exist"
        rolsuper, rolcreatedb, rolcreaterole, rolbypassrls, rolcanlogin = role_flags
        assert rolcanlogin is True
        assert rolsuper is False
        assert rolcreatedb is False
        assert rolcreaterole is False
        assert rolbypassrls is False

        for schema_name in EXPECTED_LOGICAL_SCHEMAS:
            cur.execute(
                "SELECT has_schema_privilege(%s, %s, 'USAGE'), has_schema_privilege(%s, %s, 'CREATE')",
                (app_user, schema_name, app_user, schema_name),
            )
            privilege_row = cur.fetchone()
            assert privilege_row is not None
            has_usage, has_create = privilege_row
            assert has_usage is True, f"{app_user} lacks USAGE on {schema_name}"
            assert has_create is False, f"{app_user} should not have CREATE on {schema_name}"

        cur.execute("SELECT has_schema_privilege(%s, 'public', 'CREATE')", (app_user,))
        public_create = cur.fetchone()
        assert public_create is not None and public_create[0] is False


@pytest.mark.integration
def test_live_redis_authentication_enforced() -> None:
    """Verify live Redis enforces authentication and responds to authenticated PING."""
    _require_live_integration()
    redis_url = os.environ.get("INTEGRATION_REDIS_URL", "").strip()
    if not redis_url:
        pytest.fail("INTEGRATION_REDIS_URL must be set when NEXTRADE_RUN_LIVE_INTEGRATION=1.")

    unauth_host = os.environ.get("INTEGRATION_REDIS_HOST", "127.0.0.1")
    unauth_port = int(os.environ.get("INTEGRATION_REDIS_PORT", "6381"))
    unauth_client = redis.Redis(
        host=unauth_host,
        port=unauth_port,
        socket_connect_timeout=3.0,
        socket_timeout=3.0,
    )
    try:
        with pytest.raises(redis.AuthenticationError):
            unauth_client.ping()
    finally:
        unauth_client.close()

    auth_client = redis.Redis.from_url(
        redis_url,
        socket_connect_timeout=3.0,
        socket_timeout=3.0,
        decode_responses=True,
    )
    try:
        assert auth_client.ping() is True
    finally:
        auth_client.close()


@pytest.mark.integration
def test_live_web_foundation_renders() -> None:
    """Verify live Next.js foundation route responds with security headers and core copy."""
    _require_live_integration()
    web_base = os.environ.get("INTEGRATION_WEB_BASE_URL", "").strip().rstrip("/")
    if not web_base:
        pytest.skip("INTEGRATION_WEB_BASE_URL not configured for web route check.")

    with httpx.Client(base_url=web_base, timeout=5.0) as client:
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.headers.get("x-content-type-options") == "nosniff"
        assert resp.headers.get("x-frame-options") == "DENY"
        assert "NEXTRADE AI" in resp.text
