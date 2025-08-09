from __future__ import annotations

from typing import Any

import httpx

from config.settings import get_settings

settings = get_settings()


class APIClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=str(settings.BOT_API_BASE),
            timeout=httpx.Timeout(connect=settings.CONNECT_TIMEOUT, read=settings.READ_TIMEOUT),
        )

    async def health(self) -> dict[str, Any]:
        r = await self._client.get("/healthz")
        r.raise_for_status()
        return r.json()  # type: ignore[return-value]

    async def close(self) -> None:
        await self._client.aclose()
