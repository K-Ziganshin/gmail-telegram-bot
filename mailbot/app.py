"""Entry point: logging, Gmail auth, background inbox loop and Telegram polling."""

from __future__ import annotations

import asyncio
import logging
import os
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from .config import Settings
from .gmail_client import GmailClient, build_service
from .handlers import Monitor, auto_check_loop, build_router

log = logging.getLogger("mailbot")


def setup_logging() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)-7s %(name)s: %(message)s"
    )
    logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)


async def main() -> None:
    setup_logging()
    settings = Settings.from_env()
    service = await asyncio.to_thread(build_service, settings.credentials_path, settings.token_path)
    log.info("Connected to Gmail API")

    mon = Monitor(
        gmail=GmailClient(service),
        owner_chat_id=settings.owner_chat_id,
        interval=settings.check_interval,
        tz=ZoneInfo(os.getenv("TZ_NAME", "Asia/Yekaterinburg")),
    )
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(build_router(mon))

    loop_task = asyncio.create_task(auto_check_loop(bot, mon), name="inbox-loop")  # keep a reference
    try:
        log.info("Bot started, checking every %ds", settings.check_interval)
        await dp.start_polling(bot)
    finally:
        loop_task.cancel()
        await bot.session.close()


def run() -> None:
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Stopped")
