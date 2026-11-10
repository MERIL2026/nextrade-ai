from __future__ import annotations

from typing import cast

import pytest
from pydantic import ValidationError

from app.core.config import AppEnv, Settings
from tests.conftest import make_test_settings


@pytest.mark.unit
def test_settings_normalizes_postgresql_scheme_and_cors_strings() -> None:
    settings = make_test_settings(
        api_prefix="/api/v1/",
        cors_origins="http://localhost:3000/, https://app.example.com/",
        database_url="postgresql://nextrade_app:test_pass@localhost:5435/nextrade",
    )
    assert settings.api_prefix == "/api/v1"
    assert settings.cors_origins == ["http://localhost:3000", "https://app.example.com"]
    assert settings.sqlalchemy_database_uri.startswith("postgresql+psycopg://")
    assert settings.docs_enabled is True


@pytest.mark.unit
def test_settings_parses_json_array_cors_origins() -> None:
    settings = make_test_settings(cors_origins='["http://localhost:3000", "http://127.0.0.1:3000"]')
    assert settings.cors_origins == ["http://localhost:3000", "http://127.0.0.1:3000"]


@pytest.mark.unit
def test_settings_rejects_wildcard_cors() -> None:
    with pytest.raises(ValidationError, match="Wildcard '\\*' is prohibited"):
        make_test_settings(cors_origins="*")


@pytest.mark.unit
def test_settings_rejects_non_postgres_database_url() -> None:
    with pytest.raises(ValidationError, match="postgresql"):
        make_test_settings(database_url="sqlite:///./local.db")


@pytest.mark.unit
def test_settings_rejects_non_redis_url() -> None:
    with pytest.raises(ValidationError, match="redis://"):
        make_test_settings(redis_url="http://localhost:6381/0")


@pytest.mark.unit
@pytest.mark.parametrize(
    "overrides",
    [
        {"app_env": "production", "debug": True},
        {
            "app_env": "staging",
            "app_secret": "REPLACE_WITH_MIN_32_CHAR_HIGH_ENTROPY_SECRET",
            "cors_origins": ["https://staging.example.com"],
        },
        {
            "app_env": "production",
            "app_secret": "too-short-secret",
            "cors_origins": ["https://app.example.com"],
        },
        {
            "app_env": "production",
            "app_secret": "A" * 48,
            "database_url": "postgresql+psycopg://nextrade_app:REPLACE_WITH_LOCAL_APP_PASSWORD@postgres:5432/nextrade",
            "cors_origins": ["https://app.example.com"],
        },
        {
            "app_env": "production",
            "app_secret": "A" * 48,
            "redis_url": "redis://:REPLACE_WITH_LOCAL_REDIS_PASSWORD@redis:6379/0",
            "cors_origins": ["https://app.example.com"],
        },
        {
            "app_env": "production",
            "app_secret": "A" * 48,
            "cors_origins": ["http://insecure.example.com"],
        },
        {
            "app_env": "staging",
            "app_secret": "A" * 48,
            "cors_origins": [],
        },
    ],
)
def test_settings_fail_closed_in_staging_and_production(overrides: dict[str, object]) -> None:
    base: dict[str, object] = {
        "app_secret": "A" * 48,
        "cors_origins": ["https://app.example.com"],
    }
    base.update(overrides)
    app_env = cast(AppEnv, base.get("app_env", "production"))
    cors_origins = cast(list[str], base["cors_origins"])
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url=str(
                base.get(
                    "database_url",
                    "postgresql+psycopg://nextrade_app:real_non_placeholder@postgres:5432/nextrade",
                )
            ),
            redis_url=str(
                base.get(
                    "redis_url",
                    "redis://:real_non_placeholder@redis:6379/0",
                )
            ),
            app_env=app_env,
            debug=bool(base.get("debug", False)),
            app_secret=str(base["app_secret"]),
            cors_origins=cors_origins,
        )


@pytest.mark.unit
def test_docs_disabled_by_default_outside_local_and_test() -> None:
    prod_settings = make_test_settings(
        app_env="production",
        app_secret="P" * 48,
        cors_origins=["https://app.example.com"],
    )
    assert prod_settings.docs_enabled is False
