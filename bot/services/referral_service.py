"""
Business logic for the referral system: codes, click tracking, and a
pluggable reward engine.

This module is deliberately campaign-agnostic — it has no knowledge of
giveaways, tickets, or any other reward-specific concept. A campaign
(today: "giveaway_entry") plugs in by registering a
ReferralRewardHandler via register_reward_handler(); see
bot/services/referral_reward_handlers.py for the one that exists today,
and bot/loader.py for where it's wired up at startup. A future
campaign (a different reward, a non-giveaway campaign) adds a new
handler and calls handle_conversion() with a new campaign_type —
nothing in this file changes.

Crediting is deferred to a verified conversion, never to /start, to
prevent fake-join farming: see handle_conversion(), invoked from
bot/handlers/user/participate.py once EntryService.join() succeeds.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Protocol

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from bot.db.models import User
from bot.db.repositories.referral_repo import ReferralRewardRepository, ReferralStats
from bot.db.repositories.user_repo import UserRepository
from bot.utils.formatting import pluralize
from bot.utils.security import generate_referral_code

logger = logging.getLogger(__name__)

_MAX_CODE_GENERATION_ATTEMPTS = 5

# Carries the referrer's current totals (as of the instant this reward
# was granted) so they see the updated count the moment they're
# notified — the Invite Friends screen itself is a static message that
# never self-updates, so without this the referrer would only see a
# fresh count by manually reopening it.
_NOTIFICATION_TEMPLATE = (
    "🎉 <b>New referral!</b>\n\n"
    "{referred_name} joined using your invite link.\n\n"
    "{description}\n\n"
    "👥 {friend_count} {friend_word} joined · 🎟 {entry_count} bonus {entry_word} earned"
)

# Per-(referrer, referred, campaign) mutex around the check-then-grant-
# then-record sequence in _try_grant_and_notify. Two independent trigger
# points can now race for the exact same reward — handle_conversion
# (fired by the referred user's own join) and reconcile_pending_rewards
# (fired by the referrer's own join) — if both users happen to join
# around the same moment. The referral_rewards UNIQUE constraint stops
# a duplicate ledger row either way, but a reward handler's side effect
# (e.g. EntryRepository.add_tickets) would already have run twice by
# the time that conflict is caught. In-process only is sufficient here —
# this project runs as a single bot process on one VPS.
_reward_locks: dict[tuple[int, int, str, int | None], asyncio.Lock] = defaultdict(asyncio.Lock)


@dataclass(slots=True)
class RewardOutcome:
    """What a campaign's reward handler granted — used for the ledger entry and the referrer's notification."""

    reward_type: str
    reward_amount: int
    description: str  # short human-readable fragment, e.g. "+1 ticket added."


class ReferralRewardHandler(Protocol):
    """
    A pluggable reward rule for one campaign_type. Implementations live
    outside this module (see bot/services/referral_reward_handlers.py)
    so the engine never imports anything campaign-specific.
    """

    async def grant(self, referrer_id: int, referred_id: int, campaign_id: int | None) -> RewardOutcome | None:
        """Applies the reward if eligible; returns None if not (no reward, no notification)."""
        ...


_reward_handlers: dict[str, ReferralRewardHandler] = {}


def register_reward_handler(campaign_type: str, handler: ReferralRewardHandler) -> None:
    """Registers the reward rule for a campaign_type. Called once at startup — see bot/loader.py."""
    _reward_handlers[campaign_type] = handler


class ReferralService:
    """Coordinates referral codes, click tracking, and reward crediting on top of the repositories."""

    def __init__(self, referral_repo: ReferralRewardRepository, user_repo: UserRepository) -> None:
        self._referral_repo = referral_repo
        self._user_repo = user_repo

    async def get_or_create_referral_code(self, user: User) -> str:
        """Returns the user's stable referral code, generating and persisting one if missing."""
        if user.referral_code:
            return user.referral_code
        for _ in range(_MAX_CODE_GENERATION_ATTEMPTS):
            code = generate_referral_code()
            if await self._user_repo.get_by_referral_code(code) is None:
                await self._user_repo.set_referral_code(user.id, code)
                return code
        raise RuntimeError("Could not generate a unique referral code")

    async def get_stats(self, user_id: int) -> ReferralStats:
        """Returns this user's successful-referral count and total giveaway entries earned from them."""
        return await self._referral_repo.get_stats_for_referrer(user_id)

    async def record_pending_referral(self, referred_user_id: int, referrer_code: str) -> None:
        """
        Records that referred_user_id arrived via referrer_code, without
        granting anything yet. No-ops on self-referral, an unknown code,
        or if this user already has a pending or finalized referrer
        (first-touch wins — see UserRepository.set_pending_referrer).
        """
        referrer = await self._user_repo.get_by_referral_code(referrer_code)
        if referrer is None or referrer.id == referred_user_id:
            return
        await self._user_repo.set_pending_referrer(referred_user_id, referrer.id)

    async def handle_conversion(
        self,
        bot: Bot,
        referred_user_id: int,
        campaign_type: str,
        campaign_id: int | None,
    ) -> None:
        """
        Called by a campaign whenever a referred user completes whatever
        that campaign considers a qualifying action (today: a verified
        giveaway entry). Finalizes the referral relationship — permanent
        and campaign-independent, regardless of whether a reward turns
        out to be grantable — then attempts the reward for this specific
        campaign. That attempt can fail (e.g. GiveawayEntryRewardHandler
        requires the referrer to have joined the same giveaway); since
        this only ever fires once, at the referred user's own one-time
        join, a reward that wasn't grantable *yet* would otherwise be
        lost forever with nothing to retry it — see
        reconcile_pending_rewards for the other half of that fix.
        """
        referred = await self._user_repo.get_by_id(referred_user_id)
        if referred is None or referred.pending_referrer_id is None:
            return

        referrer_id = referred.pending_referrer_id
        if referrer_id == referred_user_id:
            return  # defense in depth — record_pending_referral already blocks this at click time

        await self._user_repo.finalize_referral(referred_user_id, referrer_id)

        referrer = await self._user_repo.get_by_id(referrer_id)
        if referrer is None or referrer.is_banned or referred.is_banned:
            return

        await self._try_grant_and_notify(bot, referrer, referred, campaign_type, campaign_id)

    async def reconcile_pending_rewards(
        self,
        bot: Bot,
        referrer_id: int,
        campaign_type: str,
        campaign_id: int | None,
    ) -> None:
        """
        Called whenever a user completes a qualifying action as a
        *referrer* (e.g. joining a giveaway themselves) — the flip side
        of handle_conversion. Some reward handlers only grant once the
        referrer is themselves eligible; if a friend they'd already
        referred converted *before* the referrer became eligible,
        handle_conversion's one-shot attempt would have found it not
        grantable yet, and nothing else would ever recheck it. This
        walks every user this referrer has ever been permanently
        attributed to and retries the reward for this campaign — the
        reward handler itself (see GiveawayEntryRewardHandler.grant)
        decides whether each one is actually eligible for it.
        """
        if campaign_type not in _reward_handlers:
            return

        referrer = await self._user_repo.get_by_id(referrer_id)
        if referrer is None or referrer.is_banned:
            return

        for referred in await self._user_repo.list_referred_by(referrer_id):
            if referred.is_banned:
                continue
            await self._try_grant_and_notify(bot, referrer, referred, campaign_type, campaign_id)

    async def _try_grant_and_notify(
        self,
        bot: Bot,
        referrer: User,
        referred: User,
        campaign_type: str,
        campaign_id: int | None,
    ) -> None:
        """Shared by handle_conversion and reconcile_pending_rewards — see both for why two triggers exist."""
        handler = _reward_handlers.get(campaign_type)
        if handler is None:
            return

        lock_key = (referrer.id, referred.id, campaign_type, campaign_id)
        async with _reward_locks[lock_key]:
            if await self._referral_repo.get(referrer.id, referred.id, campaign_type, campaign_id) is not None:
                return  # already rewarded for this exact campaign — nothing new to grant or announce

            outcome = await handler.grant(referrer.id, referred.id, campaign_id)
            if outcome is None:
                return

            await self._referral_repo.create(
                referrer_id=referrer.id,
                referred_id=referred.id,
                campaign_type=campaign_type,
                campaign_id=campaign_id,
                reward_type=outcome.reward_type,
                reward_amount=outcome.reward_amount,
            )
            # Read the just-updated totals inside the same lock, so this
            # can't race with another grant landing for this referrer
            # between the write above and this read.
            stats = await self._referral_repo.get_stats_for_referrer(referrer.id)

        referred_name = referred.first_name or referred.username or "Someone"
        text = _NOTIFICATION_TEMPLATE.format(
            referred_name=referred_name,
            description=outcome.description,
            friend_count=stats.successful_referrals,
            friend_word=pluralize(stats.successful_referrals, "friend", "friends"),
            entry_count=stats.entries_earned,
            entry_word=pluralize(stats.entries_earned, "entry", "entries"),
        )
        try:
            await bot.send_message(referrer.telegram_id, text)
        except TelegramAPIError:
            logger.warning("Could not notify referrer %s of a reward", referrer.telegram_id)
