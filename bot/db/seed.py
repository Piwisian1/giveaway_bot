"""
One-time startup seeding for tables an admin would otherwise have to
populate by hand before the bot is usable. Currently just the
required-channels gate — see bot/required_channels_config.py.
"""

import logging

from bot.db.repositories.required_channel_repo import RequiredChannelRepository
from bot.required_channels_config import REQUIRED_CHANNELS

logger = logging.getLogger(__name__)


async def seed_required_channels(repo: RequiredChannelRepository) -> None:
    """
    Inserts REQUIRED_CHANNELS into the required_channels table, but
    only if the table is still empty — never overwrites channels an
    admin has since added or removed via the /admin panel, which is
    the live source of truth from the first run onward.
    """
    if not REQUIRED_CHANNELS:
        return
    if await repo.list_all():
        return

    for index, channel in enumerate(REQUIRED_CHANNELS):
        await repo.create(
            telegram_chat_id=channel.chat_id,
            title=channel.display_name,
            username=channel.username,
            invite_link=channel.invite_link,
            sort_order=index,
        )
    logger.info("Seeded %d required channel(s) from required_channels_config.py", len(REQUIRED_CHANNELS))
