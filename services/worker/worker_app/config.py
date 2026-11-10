from __future__ import annotations

from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AppEnv = Literal["local", "test", "staging", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

_PLACEHOLDER_MARKERS = (
    "REPLACE_WITH_",
    "CHANGE_ME",
    "YOUR_",
    "EXAMPLE_",
    "DEV-SECRET",
    "DEV_SECRET",
)


def _contains_placeholder(value: str) -> bool:
    upper = value.strip().upper()
    return any(marker in upper for marker in _PLACEHOLDER_MARKERS)


class WorkerSettings(BaseSettings):
    """Configuration for NEXTRADE AI Celery worker and scheduler."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    service_name: str = "nextrade-worker"
    app_env: AppEnv = "local"
    log_level: LogLevel = "INFO"

    celery_broker_url: SecretStr
    celery_result_backend: SecretStr

    worker_concurrency: int = 2
    task_time_limit_seconds: int = 300
    task_soft_time_limit_seconds: int = 240
    heartbeat_interval_seconds: float = 300.0

    @field_validator("celery_broker_url", "celery_result_backend")
    @classmethod
    def validate_redis_dsn(cls, value: SecretStr) -> SecretStr:
        raw = value.get_secret_value().strip()
        if not raw:
            raise ValueError("Worker Redis URL must not be empty.")
        parsed = urlparse(raw)
        if parsed.scheme not in {"redis", "rediss"} or not parsed.hostname:
            raise ValueError("Worker broker/backend URL must use redis:// or rediss:// scheme.")
        return SecretStr(raw)

    @model_validator(mode="after")
    def validate_environment_security(self) -> WorkerSettings:
        if self.app_env in {"staging", "production"}:
            if _contains_placeholder(self.celery_broker_url.get_secret_value()):
                raise ValueError("CELERY_BROKER_URL contains placeholder credentials.")
            if _contains_placeholder(self.celery_result_backend.get_secret_value()):
                raise ValueError("CELERY_RESULT_BACKEND contains placeholder credentials.")
        return self


@lru_cache(maxsize=1)
def get_worker_settings() -> WorkerSettings:
    """Return cached worker settings."""
    return WorkerSettings()
