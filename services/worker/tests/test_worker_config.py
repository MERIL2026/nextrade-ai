from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

WORKER_ROOT = Path(__file__).resolve().parents[1]
if str(WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKER_ROOT))

from worker_app.celery_app import create_celery_app  # noqa: E402
from worker_app.config import WorkerSettings  # noqa: E402
from worker_app.logging import WorkerJsonFormatter  # noqa: E402
from worker_app.tasks.system import heartbeat  # noqa: E402


def _make_worker_settings(**overrides: object) -> WorkerSettings:
    defaults: dict[str, object] = {
        "app_env": "test",
        "log_level": "INFO",
        "celery_broker_url": "redis://:test_pass@localhost:6381/1",
        "celery_result_backend": "redis://:test_pass@localhost:6381/2",
    }
    defaults.update(overrides)
    return WorkerSettings(_env_file=None, **defaults)  # type: ignore[arg-type]


@pytest.mark.unit
def test_worker_settings_rejects_invalid_scheme_and_prod_placeholders() -> None:
    with pytest.raises(ValidationError):
        _make_worker_settings(celery_broker_url="http://localhost:6381/1")

    with pytest.raises(ValidationError):
        _make_worker_settings(
            app_env="production",
            celery_broker_url="redis://:REPLACE_WITH_LOCAL_REDIS_PASSWORD@redis:6379/1",
        )


@pytest.mark.unit
def test_create_celery_app_registers_heartbeat_and_schedule() -> None:
    celery_app = create_celery_app(_make_worker_settings())
    assert celery_app.conf.timezone == "UTC"
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.worker_hijack_root_logger is False
    assert "ops-phase1-heartbeat" in celery_app.conf.beat_schedule
    assert celery_app.conf.beat_schedule["ops-phase1-heartbeat"]["task"] == "ops.heartbeat"
    assert "ops.heartbeat" in celery_app.tasks


@pytest.mark.unit
def test_heartbeat_task_returns_structured_status() -> None:
    result = heartbeat.run()
    assert result["status"] == "ok"
    assert result["task"] == "ops.heartbeat"
    assert result["recorded_at"].endswith("Z")


@pytest.mark.unit
def test_worker_json_formatter_scrubs_credentials() -> None:
    formatter = WorkerJsonFormatter(service="nextrade-worker", environment="test")
    record = logging.LogRecord(
        name="worker_app.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Connected broker redis://:super_secret_redis@redis:6379/1",
        args=(),
        exc_info=None,
    )
    rendered = formatter.format(record)
    assert "super_secret_redis" not in rendered
    assert "[REDACTED]" in rendered
