"""
Entrypoint.

Startup sequence:
  1. Configuration is loaded from .env as soon as bot.config is imported.
  2. Logging is configured (console + rotating file handlers under logs/).
  3. The SQLite connection is opened and the schema is created if
     needed, then the required-channels table is seeded from
     bot/required_channels_config.py if it's still empty.
  4. The aiogram Bot and Dispatcher are built, with every router registered.
  5. The auto-closer background task starts (see
     bot/background/auto_closer.py) — it runs independently of polling,
     so it keeps closing overdue giveaways even if no one is interacting
     with the bot.
  6. Any leftover webhook is cleared (long polling is this project's
     transport — see architecture doc, section 9).
  7. The bot starts long polling until interrupted, then shuts down
     cleanly: the auto-closer is cancelled first, then the database
     connection is closed last.
"""

import asyncio
import contextlib
import logging

from aiogram.types import BotCommand

from bot.background.auto_closer import auto_closer_task
from bot.config import settings
from bot.logging_config import configure_logging
from bot.loader import create_bot, create_dispatcher
from bot.db.connection import get_connection
from bot.db.repositories.required_channel_repo import RequiredChannelRepository
from bot.db.schema import init_schema
from bot.db.seed import seed_required_channels

logger = logging.getLogger(__name__)

# Public command list shown in Telegram's native "/" menu. /admin is
# deliberately excluded — it's only meant to be known to admins.
_PUBLIC_COMMANDS = (
    BotCommand(command="start", description="Open the giveaway"),
    BotCommand(command="profile", description="Your profile"),
    BotCommand(command="tickets", description="Your tickets"),
)


async def main() -> None:
    configure_logging(settings.log_dir)
    logger.info("Starting Giveaway Bot...")

    db = get_connection()
    await db.start()
    await init_schema()
    await seed_required_channels(RequiredChannelRepository(db))
    logger.info("Database ready at %s", settings.db_path)

    bot = create_bot()
    dp = create_dispatcher()

    auto_closer = asyncio.create_task(auto_closer_task(bot), name="auto-closer")

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await bot.set_my_commands(list(_PUBLIC_COMMANDS))
        me = await bot.get_me()
        logger.info("Authenticated as @%s (id=%s)", me.username, me.id)
        # Cached once so screens building a referral deep link (see
        # bot/handlers/user/referral.py) never need an extra API call.
        dp["bot_username"] = me.username

        logger.info("Starting long polling.")
        await dp.start_polling(bot)
    finally:
        auto_closer.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await auto_closer
        await bot.session.close()
        await db.stop()
        logger.info("Bot session closed.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown requested, exiting.")
