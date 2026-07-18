"""
The join flow after the Main Giveaway Card: Required Channels, Almost
There, Already Participating, and Registration Success. Screen copy and
button hierarchy follow the UX specification exactly — see
bot/formatters/participate_card.py and bot/keyboards/user_kb.py.

Required channels are read from the required_channels table (see
bot/db/repositories/required_channel_repo.py) — never hardcoded.
Subscription is verified live via the Bot API (see
RequiredChannelService.get_missing_channels, backed by
bot.get_chat_member) — never trusted from user input.

A visitor who already has an entry for the active giveaway never
repeats a check they've already passed: tapping Join Giveaway again
skips straight to Already Participating instead of re-showing the
required channels.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot.db.connection import get_connection
from bot.db.repositories.entry_repo import EntryRepository
from bot.db.repositories.giveaway_repo import GiveawayRepository
from bot.db.repositories.referral_repo import ReferralRewardRepository
from bot.db.repositories.required_channel_repo import RequiredChannelRepository
from bot.db.repositories.user_repo import UserRepository
from bot.formatters.giveaway_card import NO_ACTIVE_GIVEAWAY
from bot.formatters.participate_card import (
    render_already_participating,
    render_missing_channels,
    render_participate_screen,
    render_verified,
)
from bot.keyboards.user_kb import confirmation_kb, main_menu_kb, participate_kb
from bot.services.entry_service import EntryService
from bot.services.giveaway_service import GiveawayService
from bot.services.referral_reward_handlers import CAMPAIGN_TYPE
from bot.services.referral_service import ReferralService
from bot.services.required_channel_service import RequiredChannelService

router = Router(name="user_participate")


@router.callback_query(F.data == "menu:participate")
async def show_participate_screen(callback: CallbackQuery) -> None:
    """Shows Required Channels, or short-circuits to a state that doesn't need them."""
    connection = get_connection()
    giveaway = await GiveawayService(GiveawayRepository(connection)).get_active()
    if giveaway is None:
        await callback.message.edit_text(NO_ACTIVE_GIVEAWAY, reply_markup=main_menu_kb())
        await callback.answer()
        return

    # UserTrackingMiddleware has already upserted this user by the time
    # any handler runs — safe to just read the row back.
    user = await UserRepository(connection).get_by_telegram_id(callback.from_user.id)
    already_entered = await EntryService(EntryRepository(connection)).has_entered(giveaway.id, user.id)
    if already_entered:
        await callback.message.edit_text(
            render_already_participating(giveaway.end_at),
            reply_markup=confirmation_kb(),
        )
        await callback.answer()
        return

    channels = await RequiredChannelService(RequiredChannelRepository(connection)).get_active_channels()
    await callback.message.edit_text(
        render_participate_screen(channels),
        reply_markup=participate_kb(channels),
    )
    await callback.answer()


@router.callback_query(F.data == "participate:check_subscription")
async def check_subscription(callback: CallbackQuery) -> None:
    """Verifies required-channel membership and, if eligible, registers the entry."""
    connection = get_connection()
    giveaway = await GiveawayService(GiveawayRepository(connection)).get_active()
    if giveaway is None:
        await callback.message.edit_text(NO_ACTIVE_GIVEAWAY, reply_markup=main_menu_kb())
        await callback.answer()
        return

    channel_service = RequiredChannelService(RequiredChannelRepository(connection))
    channels = await channel_service.get_active_channels()
    missing = await channel_service.get_missing_channels(callback.bot, callback.from_user.id, channels)
    if missing:
        await callback.message.edit_text(
            render_missing_channels(missing),
            reply_markup=participate_kb(missing, retry=True),
        )
        await callback.answer("❌ Not joined yet")
        return

    user = await UserRepository(connection).get_by_telegram_id(callback.from_user.id)

    entry_service = EntryService(EntryRepository(connection))
    if await entry_service.has_entered(giveaway.id, user.id):
        await callback.message.edit_text(
            render_already_participating(giveaway.end_at),
            reply_markup=confirmation_kb(),
        )
        await callback.answer()
        return

    joined = await entry_service.join(giveaway.id, user.id)
    if not joined:
        # The giveaway closed in the gap between the get_active() read
        # above and this write (see EntryRepository.create) — rare, but
        # real without this check: channel-membership verification can
        # take long enough to matter. Must not show a false success.
        await callback.message.edit_text(NO_ACTIVE_GIVEAWAY, reply_markup=main_menu_kb())
        await callback.answer("This giveaway just ended.", show_alert=True)
        return

    ticket_number = await entry_service.count_participants(giveaway.id)

    # Referral crediting is entirely self-contained: it's a no-op if
    # this user wasn't referred, if the referrer isn't eligible, or if
    # this exact referral was already rewarded — see
    # bot/services/referral_service.py::handle_conversion. Two
    # independent checks run here since this join could be the missing
    # piece for either role: handle_conversion covers "I was referred,
    # and my join is the qualifying action"; reconcile_pending_rewards
    # covers "I referred someone who already qualified, and my own join
    # is what makes their reward grantable now" (see its docstring for
    # why that second case needs an explicit recheck at all).
    referral_service = ReferralService(ReferralRewardRepository(connection), UserRepository(connection))
    await referral_service.handle_conversion(callback.bot, user.id, CAMPAIGN_TYPE, giveaway.id)
    await referral_service.reconcile_pending_rewards(callback.bot, user.id, CAMPAIGN_TYPE, giveaway.id)

    await callback.message.edit_text(
        render_verified(entered=True, ticket_number=ticket_number, end_at=giveaway.end_at),
        reply_markup=confirmation_kb(),
    )
    await callback.answer()
