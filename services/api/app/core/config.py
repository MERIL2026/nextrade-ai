from functools import lru_cache
from typing import Annotated, Any, Literal
from urllib.parse import urlparse

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

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


class Settings(BaseSettings):
    """Application settings loaded from environment variables with fail-closed validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "NEXTRADE AI"
    app_version: str = "0.1.0"
    service_name: str = "nextrade-api"
    app_env: AppEnv = "local"
    debug: bool = False
    log_level: LogLevel = "INFO"
    api_prefix: str = "/api/v1"

    app_secret: SecretStr

    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )

    database_url: SecretStr
    migration_database_url: SecretStr | None = None
    db_pool_size: int = Field(default=5, ge=1, le=50)
    db_max_overflow: int = Field(default=5, ge=0, le=50)
    db_pool_timeout_seconds: float = Field(default=5.0, gt=0.0, le=60.0)

    redis_url: SecretStr
    health_check_timeout_seconds: float = Field(default=2.5, gt=0.1, le=30.0)
    enable_docs: bool | None = None

    @field_validator("api_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.startswith("/"):
            raise ValueError("API_PREFIX must start with '/'.")
        if len(cleaned) > 1:
            cleaned = cleaned.rstrip("/")
        return cleaned

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return []
            if raw.startswith("["):
                import json

                parsed = json.loads(raw)
                if not isinstance(parsed, list):
                    raise ValueError("CORS_ORIGINS JSON must be a list of origin strings.")
                items = [str(item) for item in parsed]
            else:
                items = [part for part in raw.split(",")]
        elif isinstance(value, list | tuple | set):
            items = [str(item) for item in value]
        else:
            raise ValueError("CORS_ORIGINS must be a list or comma-separated string.")

        normalized: list[str] = []
        for item in items:
            origin = item.strip().rstrip("/")
            if not origin:
                continue
            if origin == "*":
                raise ValueError(
                    "Wildcard '*' is prohibited in CORS_ORIGINS; specify an explicit origin allowlist."
                )
            parsed_url = urlparse(origin)
            if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
                raise ValueError(f"Invalid CORS origin format: {origin!r}")
            normalized.append(origin)
        return normalized

    @field_validator("database_url", "migration_database_url")
    @classmethod
    def validate_database_dsn(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None:
            return None
        raw = value.get_secret_value().strip()
        if not raw:
            raise ValueError("Database connection string must not be empty.")
        parsed = urlparse(raw)
        if parsed.scheme not in {"postgresql", "postgresql+psycopg"}:
            raise ValueError(
                "DATABASE_URL must use 'postgresql+psycopg://' or 'postgresql://' scheme."
            )
        if not parsed.hostname or not parsed.path.lstrip("/"):
            raise ValueError("Database URL must include hostname and database name.")
        return SecretStr(raw)

    @field_validator("redis_url")
    @classmethod
    def validate_redis_dsn(cls, value: SecretStr) -> SecretStr:
        raw = value.get_secret_value().strip()
        if not raw:
            raise ValueError("REDIS_URL must not be empty.")
        parsed = urlparse(raw)
        if parsed.scheme not in {"redis", "rediss"}:
            raise ValueError("REDIS_URL must use 'redis://' or 'rediss://' scheme.")
        if not parsed.hostname:
            raise ValueError("REDIS_URL must include hostname.")
        return SecretStr(raw)

    @model_validator(mode="after")
    def validate_environment_security(self) -> "Settings":
        app_secret_raw = self.app_secret.get_secret_value().strip()
        if not app_secret_raw:
            raise ValueError("APP_SECRET must not be empty.")

        if self.app_env in {"staging", "production"}:
            if self.debug:
                raise ValueError("DEBUG cannot be enabled in staging or production.")
            if _contains_placeholder(app_secret_raw) or len(app_secret_raw) < 32:
                raise ValueError(
                    "APP_SECRET must be a non-placeholder secret of at least 32 characters in staging/production."
                )
            if _contains_placeholder(self.database_url.get_secret_value()):
                raise ValueError(
                    "DATABASE_URL contains placeholder credentials in staging/production."
                )
            if self.migration_database_url is not None and _contains_placeholder(
                self.migration_database_url.get_secret_value()
            ):
                raise ValueError(
                    "MIGRATION_DATABASE_URL contains placeholder credentials in staging/production."
                )
            if _contains_placeholder(self.redis_url.get_secret_value()):
                raise ValueError(
                    "REDIS_URL contains placeholder credentials in staging/production."
                )
            if not self.cors_origins:
                raise ValueError("CORS_ORIGINS must not be empty in staging/production.")
            if self.app_env == "production":
                insecure = [o for o in self.cors_origins if not o.startswith("https://")]
                if insecure:
                    raise ValueError("All CORS_ORIGINS entries must use https:// in production.")
        return self

    @property
    def docs_enabled(self) -> bool:
        if self.enable_docs is not None:
            return self.enable_docs
        return self.app_env in {"local", "test"}

    @property
    def sqlalchemy_database_uri(self) -> str:
        raw = self.database_url.get_secret_value()
        if raw.startswith("postgresql://"):
            return raw.replace("postgresql://", "postgresql+psycopg://", 1)
        return raw

    @property
    def sqlalchemy_migration_uri(self) -> str:
        raw = (
            self.migration_database_url.get_secret_value()
            if self.migration_database_url is not None
            else self.database_url.get_secret_value()
        )
        if raw.startswith("postgresql://"):
            return raw.replace("postgresql://", "postgresql+psycopg://", 1)
        return raw


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached validated application settings."""
    return Settings()
