from __future__ import annotations

import json
import logging
import re
import sys
from collections.abc import Mapping
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)
job_id_ctx: ContextVar[str | None] = ContextVar("job_id", default=None)

_REDACTED = "[REDACTED]"

_SENSITIVE_KEY_SUBSTRINGS = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "set-cookie",
    "database_url",
    "migration_database_url",
    "redis_url",
    "celery_broker_url",
    "celery_result_backend",
    "dsn",
    "credential",
    "private_key",
)

_URI_CREDENTIALS_PATTERN = re.compile(
    r"((?:postgresql(?:\+\w+)?|postgres|rediss?|amqps?|https?)://[^:/\s@]*:)([^@\s]+)(@)",
    re.IGNORECASE,
)
_AUTH_HEADER_PATTERN = re.compile(
    r"\b(Bearer|Basic|Token)\s+[A-Za-z0-9\-._~+/]+=*",
    re.IGNORECASE,
)
_KV_SECRET_PATTERN = re.compile(
    r"(?i)\b(password|passwd|secret|app_secret|api_key|token)\s*([=:])\s*([^\s,;'\"]+)"
)

_STANDARD_LOG_ATTRS = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
    }
)


def redact_text(value: str) -> str:
    """Scrub embedded credentials, bearer tokens, and secret assignments from log text."""
    scrubbed = _URI_CREDENTIALS_PATTERN.sub(rf"\1{_REDACTED}\3", value)
    scrubbed = _AUTH_HEADER_PATTERN.sub(rf"\1 {_REDACTED}", scrubbed)
    scrubbed = _KV_SECRET_PATTERN.sub(rf"\1\2{_REDACTED}", scrubbed)
    return scrubbed


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in _SENSITIVE_KEY_SUBSTRINGS)


def redact_value(key: str | None, value: Any) -> Any:
    """Recursively redact sensitive keys and string payloads."""
    if key is not None and _is_sensitive_key(key):
        return _REDACTED
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, Mapping):
        return {str(k): redact_value(str(k), v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [redact_value(None, item) for item in value]
    return value


class JsonLogFormatter(logging.Formatter):
    """Structured JSON formatter conforming to NEX-DOC-011 / NEX-DOC-018 / NEX-DOC-022."""

    def __init__(self, *, service: str, environment: str) -> None:
        super().__init__()
        self._service = service
        self._environment = environment

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC)
            .isoformat()
            .replace("+00:00", "Z"),
            "severity": record.levelname,
            "service": self._service,
            "environment": self._environment,
            "logger": record.name,
            "request_id": request_id_ctx.get(),
            "correlation_id": correlation_id_ctx.get(),
            "job_id": job_id_ctx.get(),
            "message": redact_text(record.getMessage()),
        }

        for attr_name, attr_value in record.__dict__.items():
            if attr_name in _STANDARD_LOG_ATTRS or attr_name.startswith("_"):
                continue
            payload[attr_name] = redact_value(attr_name, attr_value)

        if record.exc_info:
            formatted_exc = self.formatException(record.exc_info)
            payload["exception"] = redact_text(formatted_exc)

        return json.dumps(payload, default=str, ensure_ascii=True)


def configure_logging(*, service: str, environment: str, level: str = "INFO") -> None:
    """Configure root and server loggers for structured redacted JSON output."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter(service=service, environment=environment))

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    for noisy_logger in ("uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy.engine"):
        logger = logging.getLogger(noisy_logger)
        logger.handlers.clear()
        logger.propagate = True

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
