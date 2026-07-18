"""
Periodically checks for active giveaways past their end_at and closes
them out: draws winners via WinnerService (which notifies each winner
by DM), then notifies every configured admin that it happened, since no
human triggered it — replaces APScheduler.

Started once from run.py as a long-lived asyncio.Task and cancelled on
shutdown.
"""

import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from bot.config import settings
from bot.db.connection import DatabaseConnection, get_connection
from bot.db.models import Giveaway, Winner
from bot.db.repositories.entry_repo import EntryRepository
from bot.db.repositories.giveaway_repo import GiveawayRepository
from bot.db.repositories.required_channel_repo import RequiredChannelRepository
from bot.db.repositories.user_repo import UserRepository
from bot.db.repositories.winner_repo import WinnerRepository
from bot.services.required_channel_service import RequiredChannelService
from bot.services.winner_service import GiveawayAlreadyClosedError, WinnerService
from bot.utils.formatting import escape_html

logger = logging.getLogger(__name__)

_ADMIN_CLOSE_SUMMARY = (
    "🔒 <b>{title}</b> auto-closed (end time passed).\n{count} winner(s) drawn."
)
_ADMIN_CLOSE_NO_WINNERS = (
    "🔒 <b>{title}</b> auto-closed (end time passed).\nNo eligible entrants — no winners drawn."
)


def _winner_service(connection: DatabaseConnection) -> WinnerService:
    return WinnerService(
        WinnerRepository(connection),
        EntryRepository(connection),
        GiveawayRepository(connection),
        UserRepository(connection),
        RequiredChannelService(RequiredChannelRepository(connection)),
    )


async def auto_closer_task(bot: Bot) -> None:
    """
    Loop: every `settings.auto_close_interval` seconds, find active
    giveaways whose end_at has passed and close each one out. A failure
    on one tick (or one giveaway) is logged and never kills the loop.
    """
    while True:
        try:
            await _close_due_giveaways(bot)
        except Exception:
            logger.exception("Auto-closer tick failed")
        await asyncio.sleep(settings.auto_close_interval)


async def _close_due_giveaways(bot: Bot) -> None:
    connection = get_connection()
    due = await GiveawayRepository(connection).list_due_for_close()
    for giveaway in due:
        await _close_one(bot, connection, giveaway)


async def _close_one(bot: Bot, connection: DatabaseConnection, giveaway: Giveaway) -> None:
    try:
        winners = await _winner_service(connection).draw(bot, giveaway.id)
    except GiveawayAlreadyClosedError:
        # A manual admin force-end won the race for this one in the gap
        # between listing it as due and drawing it — nothing left to do,
        # and the admin who closed it already saw the result.
        return
    except Exception:
        logger.exception("Failed to auto-close giveaway %s", giveaway.id)
        return

    logger.info("Auto-closed giveaway %s (%s), %d winner(s) drawn", giveaway.id, giveaway.title, len(winners))
    await _notify_admins(bot, giveaway, winners)


async def _notify_admins(bot: Bot, giveaway: Giveaway, winners: list[Winner]) -> None:
    title = escape_html(giveaway.title)
    text = (
        _ADMIN_CLOSE_SUMMARY.format(title=title, count=len(winners))
        if winners
        else _ADMIN_CLOSE_NO_WINNERS.format(title=title)
    )
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, text)
        except TelegramAPIError:
            logger.warning("Could not notify admin %s of auto-close for giveaway %s", admin_id, giveaway.id)
