from __future__ import annotations

import json
import logging
import re
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

job_id_ctx: ContextVar[str | None] = ContextVar("job_id", default=None)
task_name_ctx: ContextVar[str | None] = ContextVar("task_name", default=None)

_REDACTED = "[REDACTED]"
_URI_CREDENTIALS_PATTERN = re.compile(
    r"((?:postgresql(?:\+\w+)?|postgres|rediss?|amqps?|https?)://[^:/\s@]*:)([^@\s]+)(@)",
    re.IGNORECASE,
)


def redact_text(value: str) -> str:
    """Scrub embedded credentials from worker logs."""
    return _URI_CREDENTIALS_PATTERN.sub(rf"\1{_REDACTED}\3", value)


class WorkerJsonFormatter(logging.Formatter):
    """Structured JSON log formatter for worker and beat scheduler."""

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
            "job_id": job_id_ctx.get(),
            "task_name": task_name_ctx.get(),
            "message": redact_text(record.getMessage()),
        }
        if record.exc_info:
            payload["exception"] = redact_text(self.formatException(record.exc_info))
        return json.dumps(payload, default=str, ensure_ascii=True)


def configure_worker_logging(*, service: str, environment: str, level: str = "INFO") -> None:
    """Configure root logger for structured worker logs."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(WorkerJsonFormatter(service=service, environment=environment))
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
