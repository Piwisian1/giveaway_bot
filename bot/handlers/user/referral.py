"""
"Invite Friends" screen — shows the user's personal referral link with
Share and Copy Link actions, plus how many friends have joined through
it and how many bonus entries that's earned. Not yet available: an
admin-facing leaderboard and reward settings — separate milestones.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot.db.connection import get_connection
from bot.db.repositories.referral_repo import ReferralRewardRepository
from bot.db.repositories.user_repo import UserRepository
from bot.formatters.referral_card import render_invite_screen
from bot.keyboards.user_kb import invite_kb
from bot.services.referral_service import ReferralService

router = Router(name="user_referral")


@router.callback_query(F.data == "menu:invite_friends")
async def show_referral_screen(callback: CallbackQuery, bot_username: str) -> None:
    """Shows the user's referral link, generating a code the first time they open this screen."""
    connection = get_connection()
    user = await UserRepository(connection).get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer()
        return

    service = ReferralService(ReferralRewardRepository(connection), UserRepository(connection))
    code = await service.get_or_create_referral_code(user)
    link = f"https://t.me/{bot_username}?start=ref_{code}"
    stats = await service.get_stats(user.id)

    await callback.message.edit_text(render_invite_screen(link, stats), reply_markup=invite_kb(link))
    await callback.answer()
