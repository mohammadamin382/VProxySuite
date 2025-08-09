# services/worker/src/core/runner.py
from __future__ import annotations

import asyncio
import contextlib
import json
import uuid
from dataclasses import dataclass
from typing import Any

import orjson
from pydantic import BaseModel, Field, ValidationError

from config.settings import get_settings
from core.parsers import ParseResult, parse_config
from plugins.base import (
    KIND_COMPLIANCE,
    KIND_PERFORMANCE,
    KIND_SECURITY_ADV,
    KIND_SECURITY_BASIC,
    KIND_STABILITY,
    PluginContext,
    PluginResult,
    available_kinds,
    make_plugin,
)

settings = get_settings()

# ---------------------------
# Request/Response payloads
# ---------------------------
class TaskRequest(BaseModel):
    """
    Payload produced by API Orchestrator and consumed by Worker.
    """
    task_id: uuid.UUID
    user_telegram_id: int
    username: str | None = None
    config_raw: str
    tests: list[str] = Field(min_length=1)
    consent_required: bool = False
    consent_granted: bool = False


class TaskResponse(BaseModel):
    task_id: uuid.UUID
    ok: bool
    results: dict[str, dict[str, Any]]
    warnings: list[str] = []
    errors: list[str] = []


# ---------------------------
# Runner
# ---------------------------
async def _run_single(kind: str, ctx: PluginContext) -> tuple[str, PluginResult]:
    plugin = make_plugin(kind)
    try:
        result = await asyncio.wait_for(plugin.run(ctx), timeout=ctx.timeout_sec)
        return kind, result
    except asyncio.TimeoutError:
        return kind, PluginResult(ok=False, kind=kind, error="timeout", warnings=[])
    except Exception as e:  # noqa: BLE001
        return kind, PluginResult(ok=False, kind=kind, error=str(e), warnings=[])


async def _normalize_config(raw: str) -> tuple[dict[str, Any], list[str]]:
    parsed: ParseResult = parse_config(raw)
    cfg: dict[str, Any] = parsed.config.model_dump()  # Pydantic v2
    return cfg, parsed.warnings


async def execute_request_async(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Main entry called by Celery bridge.
    """
    try:
        req = TaskRequest.model_validate(payload)
    except ValidationError as ve:
        return TaskResponse(
            task_id=uuid.UUID(payload.get("task_id", "00000000-0000-0000-0000-000000000000")),
            ok=False,
            results={},
            warnings=[],
            errors=[f"validation error: {ve}"],
        ).model_dump()

    # Normalize & validate config
    try:
        normalized_cfg, parse_warnings = await _normalize_config(req.config_raw)
    except Exception as e:  # noqa: BLE001
        return TaskResponse(
            task_id=req.task_id,
            ok=False,
            results={},
            warnings=[],
            errors=[f"config parse error: {e}"],
        ).model_dump()

    # Gate advanced tests
    requested = list(dict.fromkeys(req.tests))  # dedupe preserve order
    effective_tests: list[str] = []
    warnings: list[str] = list(parse_warnings)

    for k in requested:
        if k == KIND_SECURITY_ADV:
            if not settings.ENABLE_SECURITY_ADVANCED or not (req.consent_required and req.consent_granted):
                warnings.append("advanced security tests skipped (consent disabled or not granted).")
                continue
        effective_tests.append(k)

    # Validate kinds exist
    unknown = [k for k in effective_tests if k not in available_kinds()]
    if unknown:
        warnings.append(f"unknown/unsupported test kinds skipped: {unknown}")
        effective_tests = [k for k in effective_tests if k not in unknown]

    # Nothing to run?
    if not effective_tests:
        return TaskResponse(
            task_id=req.task_id,
            ok=False,
            results={},
            warnings=warnings,
            errors=["no effective tests to run"],
        ).model_dump()

    # Build context
    ctx = PluginContext(
        request_id=str(req.task_id),
        config=normalized_cfg,
        log_extra={"telegram_id": req.user_telegram_id, "username": req.username},
        timeout_sec=settings.DEFAULT_TASK_TIMEOUT_SEC,
    )

    # Parallelize with a soft cap to avoid overload
    sem = asyncio.Semaphore(settings.MAX_PARALLEL_PLUGINS)

    async def _guarded(kind: str) -> tuple[str, PluginResult]:
        async with sem:
            return await _run_single(kind, ctx)

    pairs = await asyncio.gather(*[_guarded(k) for k in effective_tests])

    # Aggregate
    results_map: dict[str, dict[str, Any]] = {}
    any_ok = False
    for kind, res in pairs:
        results_map[kind] = {
            "ok": res.ok,
            "metrics": res.metrics,
            "warnings": res.warnings,
            "error": res.error,
        }
        any_ok = any_ok or res.ok

    return TaskResponse(
        task_id=req.task_id, ok=any_ok, results=results_map, warnings=warnings, errors=[]
    ).model_dump()
