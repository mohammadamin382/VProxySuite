from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config.settings import get_settings
from bot.routers.start import router as start_router
from bot.middlewares import LoggingMiddleware
from utils.logging import setup_logging

settings = get_settings()


async def _startup(dp: Dispatcher) -> None:
    # Place for future startup hooks (webhook set, etc.)
    logging.getLogger(__name__).info("Bot startup complete", extra={"service": "bot"})


async def _shutdown(dp: Dispatcher, bot: Bot) -> None:
    await bot.session.close()
    logging.getLogger(__name__).info("Bot shutdown complete", extra={"service": "bot"})


async def main() -> None:
    setup_logging(settings.LOG_LEVEL)
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    # Middlewares
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())
    # Routers
    dp.include_router(start_router)

    await _startup(dp)
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await _shutdown(dp, bot)


if __name__ == "__main__":
    with suppress(KeyboardInterrupt):
        asyncio.run(main())
