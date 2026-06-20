"""
BlueHub Telegram Bot - Main Entry Point
========================================
Bot factory using aiogram 3.x with long-polling and webhook support.
Integrates i18n and authentication middleware.
"""
from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import DefaultKeyBuilder, RedisStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web as aiohttp_web

from bot.handlers import register_all_handlers
from bot.middleware.auth import AuthMiddleware
from bot.middleware.i18n import I18nMiddleware
from core.config import settings

logger = logging.getLogger(__name__)

# Global storage reference for lifecycle management
_storage = None


def _build_storage():
    """Create appropriate FSM storage based on available configuration."""
    global _storage
    if _storage is not None:
        return _storage

    if settings.REDIS_URL is not None:
        try:
            _storage = RedisStorage(
                redis=None,  # Will be injected later or use from_url
                key_builder=DefaultKeyBuilder(with_destiny=True),
            )
            logger.info("Using Redis FSM storage")
            return _storage
        except Exception as exc:
            logger.warning("Redis FSM storage not available, falling back to memory: %s", exc)

    _storage = MemoryStorage()
    logger.info("Using in-memory FSM storage")
    return _storage


async def _resolve_redis_storage() -> RedisStorage | None:
    """Attempt to create Redis storage from configured URL."""
    try:
        import redis.asyncio as aioredis

        redis_client = aioredis.from_url(
            str(settings.REDIS_URL),
            decode_responses=True,
        )
        storage = RedisStorage(
            redis=redis_client,
            key_builder=DefaultKeyBuilder(with_destiny=True),
        )
        return storage
    except Exception as exc:
        logger.warning("Could not create Redis storage, using memory storage: %s", exc)
        return None


def create_bot() -> Bot:
    """
    Create and return a configured aiogram Bot instance.

    Returns:
        Bot: Configured aiogram Bot instance
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not configured. "
            "Set it in your .env file or environment variables."
        )

    bot = Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    logger.info("Telegram bot created with token from configuration")
    return bot


async def create_dispatcher(bot: Bot) -> Dispatcher:
    """
    Create and configure the aiogram Dispatcher with all middleware and handlers.

    Args:
        bot: Configured aiogram Bot instance

    Returns:
        Dispatcher: Configured dispatcher ready to process updates
    """
    # Resolve Redis storage or fall back to memory
    global _storage
    redis_storage = await _resolve_redis_storage()
    if redis_storage is not None:
        _storage = redis_storage
    else:
        _storage = MemoryStorage()

    dp = Dispatcher(storage=_storage)

    # --- Middleware registration (order matters: outer -> inner) ---
    # 1. i18n middleware - adds T() to data for translations
    dp.update.middleware.register(I18nMiddleware())
    # 2. Auth middleware - links Telegram user to database user
    dp.update.middleware.register(AuthMiddleware())

    # --- Register all handlers ---
    register_all_handlers(dp)

    # --- Error handler ---
    @dp.errors()
    async def error_handler(update, exception):
        logger.error(
            "Unhandled exception during update processing: %s",
            exception,
            exc_info=True,
        )
        return True  # Suppress further error propagation

    logger.info("Dispatcher configured with all middleware and handlers")
    return dp


async def start_long_polling(bot: Bot, dp: Dispatcher) -> None:
    """
    Start the bot in long-polling mode (for development).

    Args:
        bot: Configured Bot instance
        dp: Configured Dispatcher instance
    """
    logger.info("Starting bot in long-polling mode...")
    await bot.delete_webhook(
        drop_pending_updates=settings.TELEGRAM_DROP_PENDING_UPDATES
    )
    await dp.start_polling(bot)


async def start_webhook(
    bot: Bot,
    dp: Dispatcher,
    host: str = "0.0.0.0",
    port: int = 8443,
    path: str = "/webhook/telegram",
) -> None:
    """
    Start the bot in webhook mode (for production).

    Args:
        bot: Configured Bot instance
        dp: Configured Dispatcher instance
        host: Host to bind the webhook server
        port: Port to bind the webhook server
        path: Webhook URL path
    """
    if not settings.TELEGRAM_WEBHOOK_URL:
        raise RuntimeError("TELEGRAM_WEBHOOK_URL must be set for webhook mode")

    webhook_url = f"{settings.TELEGRAM_WEBHOOK_URL.rstrip('/')}{path}"

    logger.info("Starting bot in webhook mode at %s", webhook_url)

    # Set webhook
    secret_token = settings.TELEGRAM_WEBHOOK_SECRET
    await bot.set_webhook(
        url=webhook_url,
        secret_token=secret_token,
        drop_pending_updates=settings.TELEGRAM_DROP_PENDING_UPDATES,
    )

    # Create aiohttp app for the webhook
    app = aiohttp_web.Application()
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=secret_token,
    )
    webhook_requests_handler.register(app, path=path)
    setup_application(app, dp, bot=bot)

    runner = aiohttp_web.AppRunner(app)
    await runner.setup()
    site = aiohttp_web.TCPSite(runner, host=host, port=port)
    await site.start()

    logger.info("Webhook server started on %s:%d%s", host, port, path)

    # Keep running
    import asyncio
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down webhook server...")
    finally:
        await bot.delete_webhook()
        await runner.cleanup()


async def run_bot(mode: str = "polling") -> None:
    """
    Convenience entry point to create and run the bot.

    Args:
        mode: 'polling' for long-polling, 'webhook' for webhook mode
    """
    bot = create_bot()
    dp = await create_dispatcher(bot)

    if mode == "webhook":
        await start_webhook(bot, dp)
    else:
        await start_long_polling(bot, dp)


__all__ = [
    "create_bot",
    "create_dispatcher",
    "start_long_polling",
    "start_webhook",
    "run_bot",
]
