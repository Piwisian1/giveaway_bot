"""
Business logic for drawing giveaway winners: cryptographically secure,
ticket-weighted random selection, with full audit logging.

Winner count isn't a stored field — a giveaway has up to four prize
tiers (first/second/third/bonus_prize, see bot/db/models.py), and one
winner is drawn per non-null tier, in that order. Position 1 is always
first_prize (required at creation); a giveaway with e.g. only
first_prize + third_prize set still draws exactly 2 winners, at
positions 1 and 2 — see _prize_tiers below.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from bot.db.models import Entry, Giveaway, Winner
from bot.db.repositories.entry_repo import EntryRepository
from bot.db.repositories.giveaway_repo import GiveawayRepository
from bot.db.repositories.user_repo import UserRepository
from bot.db.repositories.winner_repo import WinnerRepository
from bot.services.required_channel_service import RequiredChannelService
from bot.texts.en import WINNER_NOTIFICATION
from bot.utils.formatting import escape_html
from bot.utils.security import secure_choice_weighted

logger = logging.getLogger(__name__)

# Per-giveaway mutex serializing draw()/reroll() — both do a read-then-write
# sequence (list winners, delete, redraw, insert) with no single atomic SQL
# statement to fall back on the way close_if_active() covers draw()'s own
# "was this giveaway still active" check. Two overlapping calls for the same
# giveaway_id (an admin double-tapping Reroll, or two admins) would otherwise
# both draw and insert winners, and winners has no UNIQUE(giveaway_id,
# user_id) to catch it. In-process only, which is sufficient — this project
# runs as a single bot process on one VPS (see README's design notes).
_giveaway_locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)


class GiveawayAlreadyClosedError(Exception):
    """
    Raised by draw() when the giveaway was already inactive by the time
    its close was attempted — someone else (the auto-closer, or a manual
    admin action) closed it first. Callers should treat this the same as
    "nothing to do", not as a failure.
    """

    def __init__(self, giveaway_id: int) -> None:
        super().__init__(f"Giveaway {giveaway_id} was already closed")
        self.giveaway_id = giveaway_id


def _prize_tiers(giveaway: Giveaway) -> list[str]:
    """Prize text for every filled tier, in position order (gaps collapsed)."""
    tiers = (giveaway.first_prize, giveaway.second_prize, giveaway.third_prize, giveaway.bonus_prize)
    return [prize for prize in tiers if prize]


class WinnerService:
    """Coordinates winner selection on top of WinnerRepository and its sibling repos."""

    def __init__(
        self,
        winner_repo: WinnerRepository,
        entry_repo: EntryRepository,
        giveaway_repo: GiveawayRepository,
        user_repo: UserRepository,
        required_channel_service: RequiredChannelService,
    ) -> None:
        self._winner_repo = winner_repo
        self._entry_repo = entry_repo
        self._giveaway_repo = giveaway_repo
        self._user_repo = user_repo
        self._required_channel_service = required_channel_service

    async def draw(self, bot: Bot, giveaway_id: int) -> list[Winner]:
        """
        Re-verifies entrant channel membership, then draws one winner per
        filled prize tier using bot/utils/security.secure_choice_weighted,
        weighted by each entry's ticket count. Persists winners and
        notifies them by DM.

        Closing the giveaway is the *first* step, not the last: it's an
        atomic compare-and-set (see GiveawayRepository.close_if_active)
        that claims the giveaway before anything else happens, so two
        callers racing on the same giveaway (the auto-closer and a manual
        admin force-end, both running on the same event loop) can't both
        draw winners for it. The loser raises GiveawayAlreadyClosedError
        instead of drawing a duplicate set of winners.
        """
        async with _giveaway_locks[giveaway_id]:
            giveaway = await self._require_giveaway(giveaway_id)
            if not await self._giveaway_repo.close_if_active(giveaway_id):
                raise GiveawayAlreadyClosedError(giveaway_id)

            entries = await self._entry_repo.list_for_giveaway(giveaway_id)
            return await self._select_and_notify(bot, giveaway, entries)

    async def reroll(self, bot: Bot, giveaway_id: int) -> list[Winner]:
        """
        Re-draws winners for an already-ended giveaway, excluding
        everyone who won it previously so no one wins the same giveaway
        twice across rerolls.
        """
        async with _giveaway_locks[giveaway_id]:
            giveaway = await self._require_giveaway(giveaway_id)
            previous_winners = await self._winner_repo.list_for_giveaway(giveaway_id)
            excluded_user_ids = {winner.user_id for winner in previous_winners}

            entries = await self._entry_repo.list_for_giveaway(giveaway_id)
            entries = [entry for entry in entries if entry.user_id not in excluded_user_ids]

            await self._winner_repo.delete_for_giveaway(giveaway_id)
            return await self._select_and_notify(bot, giveaway, entries)

    async def _require_giveaway(self, giveaway_id: int) -> Giveaway:
        giveaway = await self._giveaway_repo.get_by_id(giveaway_id)
        if giveaway is None:
            raise ValueError(f"No giveaway with id {giveaway_id}")
        return giveaway

    async def _select_and_notify(self, bot: Bot, giveaway: Giveaway, entries: list[Entry]) -> list[Winner]:
        eligible = await self._filter_eligible(bot, entries)
        prize_tiers = _prize_tiers(giveaway)
        winner_count = min(len(prize_tiers), len(eligible))

        winners: list[Winner] = []
        if winner_count > 0:
            candidates = [entry.user_id for entry in eligible]
            weights = [entry.tickets for entry in eligible]
            chosen_user_ids = secure_choice_weighted(candidates, weights, winner_count)
            for position, user_id in enumerate(chosen_user_ids, start=1):
                winner = await self._winner_repo.create(giveaway.id, user_id, position)
                winners.append(winner)

        await self._notify_winners(bot, giveaway, winners, prize_tiers)
        return winners

    async def _filter_eligible(self, bot: Bot, entries: list[Entry]) -> list[Entry]:
        """
        Drops entries with no positive ticket weight, banned users, and
        anyone who's left a required channel since entering — entry-time
        membership is not trusted at draw time.
        """
        channels = await self._required_channel_service.get_active_channels()
        eligible = []
        for entry in entries:
            if entry.tickets <= 0:
                continue
            user = await self._user_repo.get_by_id(entry.user_id)
            if user is None or user.is_banned:
                continue
            missing = await self._required_channel_service.get_missing_channels(bot, user.telegram_id, channels)
            if missing:
                continue
            eligible.append(entry)
        return eligible

    async def _notify_winners(
        self,
        bot: Bot,
        giveaway: Giveaway,
        winners: list[Winner],
        prize_tiers: list[str],
    ) -> None:
        for winner in winners:
            user = await self._user_repo.get_by_id(winner.user_id)
            if user is None:
                continue
            prize = prize_tiers[winner.position - 1]
            text = WINNER_NOTIFICATION.format(prize=escape_html(prize), title=escape_html(giveaway.title))
            try:
                await bot.send_message(user.telegram_id, text)
            except TelegramAPIError:
                logger.warning("Could not notify winner %s of giveaway %s", user.telegram_id, giveaway.id)
                continue
            await self._winner_repo.mark_notified(winner.id)
