from __future__ import annotations

from celery import Celery

from worker_app.config import WorkerSettings, get_worker_settings
from worker_app.logging import configure_worker_logging


def create_celery_app(settings: WorkerSettings | None = None) -> Celery:
    """Create configured Celery instance with Phase 1 reliability defaults."""
    resolved = settings or get_worker_settings()
    configure_worker_logging(
        service=resolved.service_name,
        environment=resolved.app_env,
        level=resolved.log_level,
    )

    celery = Celery(
        "nextrade_worker",
        broker=resolved.celery_broker_url.get_secret_value(),
        backend=resolved.celery_result_backend.get_secret_value(),
        include=["worker_app.tasks.system"],
    )

    celery.conf.update(
        timezone="UTC",
        enable_utc=True,
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        result_expires=3600,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        worker_concurrency=resolved.worker_concurrency,
        task_time_limit=resolved.task_time_limit_seconds,
        task_soft_time_limit=resolved.task_soft_time_limit_seconds,
        broker_connection_retry_on_startup=True,
        worker_hijack_root_logger=False,
        beat_schedule={
            "ops-phase1-heartbeat": {
                "task": "ops.heartbeat",
                "schedule": resolved.heartbeat_interval_seconds,
            }
        },
    )
    return celery
