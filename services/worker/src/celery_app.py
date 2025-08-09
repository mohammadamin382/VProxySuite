# services/worker/src/celery_app.py
from __future__ import annotations

import asyncio
from typing import Any

from celery import Celery
from celery.utils.log import get_task_logger

from config.settings import get_settings
from core.runner import execute_request_async

settings = get_settings()

celery = Celery(
    main=f"{settings.CELERY_NAMESPACE}.worker",
    broker=settings.BROKER_URL,
    backend=settings.RESULT_BACKEND,
)

# Reasonable defaults
celery.conf.task_serializer = "json"
celery.conf.result_serializer = "json"
celery.conf.accept_content = ["json"]
celery.conf.task_acks_late = True
celery.conf.worker_prefetch_multiplier = 1
celery.conf.result_expires = 3600 * 12  # 12h
celery.conf.broker_connection_retry_on_startup = True

log = get_task_logger(__name__)


@celery.task(name="vproxysuite.execute_task", bind=True)
def execute_task(self, payload: dict[str, Any]) -> dict[str, Any]:
    """
    Celery entrypoint. Bridges sync Celery → async runner.
    """
    log.info("Execute task payload keys=%s", list(payload.keys()))
    return asyncio.run(execute_request_async(payload))
