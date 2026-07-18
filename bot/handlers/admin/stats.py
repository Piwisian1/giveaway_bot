"""
Admin statistics screen: total users, growth, active giveaway entrant
counts, referral leaderboard.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot.keyboards.admin_kb import admin_root_menu_kb

router = Router(name="admin_stats")

_COMING_SOON = "📊 <b>Statistics</b>\n\nStatistics are coming soon."


@router.callback_query(F.data == "admin:stats")
async def show_stats(callback: CallbackQuery) -> None:
    """Renders aggregate bot/giveaway/referral statistics."""
    # TODO: fetch aggregates via user_service / giveaway_service / referral_service
    await callback.message.edit_text(_COMING_SOON, reply_markup=admin_root_menu_kb())
    await callback.answer()
