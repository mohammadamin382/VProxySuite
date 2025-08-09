from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

log = logging.getLogger("bot.middleware")

class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        try:
            log.debug("update received: %s", type(event).__name__)
            return await handler(event, data)
        except Exception as e:  # noqa: BLE001
            log.exception("handler error: %s", e)
            raise
