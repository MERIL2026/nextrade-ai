from __future__ import annotations

import logging
from datetime import UTC, datetime

from celery import shared_task

from worker_app.logging import job_id_ctx, task_name_ctx

logger = logging.getLogger(__name__)


@shared_task(name="ops.heartbeat", bind=True, max_retries=0)
def heartbeat(self: object) -> dict[str, str]:
    """Idempotent Phase 1 health/scheduler verification task."""
    task_id = getattr(getattr(self, "request", None), "id", None) or "manual"
    jid_token = job_id_ctx.set(str(task_id))
    tname_token = task_name_ctx.set("ops.heartbeat")
    try:
        recorded_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        logger.info("Executed Phase 1 ops.heartbeat")
        return {
            "status": "ok",
            "task": "ops.heartbeat",
            "job_id": str(task_id),
            "recorded_at": recorded_at,
        }
    finally:
        task_name_ctx.reset(tname_token)
        job_id_ctx.reset(jid_token)
