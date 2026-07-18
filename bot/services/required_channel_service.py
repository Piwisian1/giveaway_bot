"""
Business logic for the required-channels list shown on the Participate
screen. Currently a thin read-only layer on top of
RequiredChannelRepository, plus live membership verification via the
Bot API; will grow admin-facing create/deactivate operations once the
admin channel-management screen is implemented.
"""

import re

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from bot.db.models import RequiredChannel
from bot.db.repositories.required_channel_repo import RequiredChannelRepository

# Chat member statuses that count as "still in the channel".
_JOINED_STATUSES = {"member", "administrator", "creator"}

_TME_USERNAME_RE = re.compile(r"^https?://t\.me/([A-Za-z0-9_]{4,})/?$")


class ChannelResolutionError(Exception):
    """Raised when admin input can't be resolved to a real, accessible channel."""


class RequiredChannelService:
    def __init__(self, repo: RequiredChannelRepository) -> None:
        self._repo = repo

    async def get_active_channels(self) -> list[RequiredChannel]:
        """Returns the channels a user currently must join, in display order."""
        return await self._repo.list_active()

    async def list_all_channels(self) -> list[RequiredChannel]:
        """Returns every configured channel, active or not — for the admin screen."""
        return await self._repo.list_all()

    async def get_by_id(self, channel_id: int) -> RequiredChannel | None:
        return await self._repo.get_by_id(channel_id)

    async def add_channel(self, bot: Bot, raw_input: str) -> RequiredChannel:
        """
        Resolves admin-supplied text (a @username or a public t.me/<username>
        link) to a real channel via the Bot API and persists it as active.

        Only public channels are supported here: getChat can only resolve a
        "@username", so a private invite-link-only channel (t.me/+..., or
        t.me/joinchat/...) can't be looked up this way. Raises
        ChannelResolutionError with a user-facing reason on any failure.
        """
        username = self._extract_username(raw_input)
        lookup_target = f"@{username}" if username else raw_input.strip()

        try:
            chat = await bot.get_chat(lookup_target)
        except TelegramAPIError as exc:
            raise ChannelResolutionError(
                "Couldn't find that channel. Make sure it's public (send its "
                "@username or https://t.me/username link) and that the bot "
                "has been added to it."
            ) from exc

        invite_link = raw_input.strip() if username is None else None
        return await self._repo.create(
            telegram_chat_id=chat.id,
            title=chat.title or lookup_target,
            username=chat.username,
            invite_link=invite_link,
        )

    async def remove_channel(self, channel_id: int) -> None:
        """Permanently removes a required channel."""
        await self._repo.delete(channel_id)

    @staticmethod
    def _extract_username(raw_input: str) -> str | None:
        """Pulls a bare username out of "@name" or "https://t.me/name" input."""
        text = raw_input.strip()
        if text.startswith("@"):
            return text[1:]
        match = _TME_USERNAME_RE.match(text)
        if match:
            return match.group(1)
        return None

    async def get_missing_channels(
        self,
        bot: Bot,
        user_telegram_id: int,
        channels: list[RequiredChannel] | None = None,
    ) -> list[RequiredChannel]:
        """
        Returns the subset of active required channels the user has NOT
        joined, verified live via getChatMember — never trusted from
        user input. A channel is treated as missing if membership can't
        be verified (e.g. the bot isn't an admin there), since that's
        the safe default for gating giveaway entry.
        """
        if channels is None:
            channels = await self.get_active_channels()

        missing = []
        for channel in channels:
            try:
                member = await bot.get_chat_member(channel.telegram_chat_id, user_telegram_id)
            except TelegramAPIError:
                missing.append(channel)
                continue
            if member.status not in _JOINED_STATUSES:
                missing.append(channel)
        return missing
