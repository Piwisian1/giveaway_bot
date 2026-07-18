"""
/start command handler.

Renders the main menu: the currently active giveaway's card (see
bot/formatters/giveaway_card.py), or a "no active giveaway" notice,
with its inline keyboard (bot/keyboards/user_kb.py main_menu_kb).

Also parses an optional deep-link payload, /start ref_<referral_code>,
and records first-touch attribution for it. No reward is granted here
— that only happens later, on a verified conversion (see
bot/services/referral_service.py::handle_conversion, wired up from
bot/handlers/user/participate.py). This deliberately mirrors
ReferralService's own separation: click tracking is generic and
doesn't care what the user goes on to do next.

The user row itself is upserted by UserTrackingMiddleware before this
handler ever runs.
"""

from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import Message

from bot.db.connection import get_connection
from bot.db.repositories.giveaway_repo import GiveawayRepository
from bot.db.repositories.referral_repo import ReferralRewardRepository
from bot.db.repositories.required_channel_repo import RequiredChannelRepository
from bot.db.repositories.user_repo import UserRepository
from bot.formatters.giveaway_card import render_active_giveaway
from bot.keyboards.user_kb import main_menu_kb
from bot.services.giveaway_service import GiveawayService
from bot.services.referral_service import ReferralService
from bot.services.required_channel_service import RequiredChannelService

router = Router(name="user_start")

_REFERRAL_PAYLOAD_PREFIX = "ref_"


@router.message(CommandStart())
async def handle_start(message: Message, command: CommandObject) -> None:
    """Entry point for new and returning users: shows the main menu card."""
    if command.args and command.args.startswith(_REFERRAL_PAYLOAD_PREFIX):
        code = command.args.removeprefix(_REFERRAL_PAYLOAD_PREFIX)
        await _record_referral_click(message, code)

    connection = get_connection()
    giveaway = await GiveawayService(GiveawayRepository(connection)).get_active()
    channels = await RequiredChannelService(RequiredChannelRepository(connection)).get_active_channels()
    await message.answer(render_active_giveaway(giveaway, len(channels)), reply_markup=main_menu_kb())


async def _record_referral_click(message: Message, referral_code: str) -> None:
    """Records the click; no-ops on self-referral, an unknown code, or an already-attributed user."""
    connection = get_connection()
    user = await UserRepository(connection).get_by_telegram_id(message.from_user.id)
    if user is None:
        return
    service = ReferralService(ReferralRewardRepository(connection), UserRepository(connection))
    await service.record_pending_referral(user.id, referral_code)
