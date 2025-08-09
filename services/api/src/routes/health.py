# services/api/src/routes/health.py
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from redis.asyncio import Redis, from_url
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from db.base import engine

router = APIRouter(tags=["health"])

_settings = get_settings()


@router.get("/healthz")
async def healthz() -> dict[str, Any]:
    """Lightweight health probe: no external checks."""
    return {"status": "ok", "service": _settings.SERVICE_NAME, "env": _settings.ENV}


@router.get("/readyz")
async def readyz() -> dict[str, Any]:
    """Readiness probe: checks DB and Redis connectivity."""
    db_ok = False
    redis_ok = False

    # DB check
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        db_ok = False

    # Redis check
    try:
        r: Redis = from_url(str(_settings.REDIS_URL), encoding="utf-8", decode_responses=True)
        await r.ping()
        await r.aclose()
        redis_ok = True
    except Exception:
        redis_ok = False

    return {"status": "ok" if db_ok and redis_ok else "degraded", "db": db_ok, "redis": redis_ok}
