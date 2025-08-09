# services/api/src/main.py
from __future__ import annotations

import contextlib
from typing import AsyncIterator

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from config.settings import get_settings
from db.base import Base, engine
from routes.health import router as health_router
from __init__ import __version__


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.SERVICE_NAME,
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Routers
    app.include_router(health_router)

    # Lifespan: create metadata in dev (migrations in prod)
    @app.on_event("startup")
    async def on_startup() -> None:
        if settings.is_dev:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        # engine uses connection pooling; dispose on shutdown
        await engine.dispose()

    return app


app = create_app()
