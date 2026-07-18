"""
Periodically refreshes every active giveaway's announcement message so
its participant count and "time remaining" stay current — without any
external scheduling dependency (replaces APScheduler).

Started once from run.py as a long-lived asyncio.Task and cancelled on
shutdown.
"""

import asyncio

from bot.config import settings


async def live_updater_task() -> None:
    """
    Loop: every `settings.live_update_interval` seconds, re-render and
    edit the announcement message of every active giveaway.

    Must tolerate Telegram's "message is not modified" error when the
    rendered text/keyboard happens to be unchanged since the last tick.
    """
    while True:
        # TODO: fetch active giveaways via giveaway_service.list_active()
        # TODO: for each, re-render via
        #       formatters/giveaway_card.render_giveaway_card(...) and call
        #       bot.edit_message_text(...) on
        #       (giveaway.announce_chat_id, giveaway.announce_message_id)
        await asyncio.sleep(settings.live_update_interval)
