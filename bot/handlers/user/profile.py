"""
Profile screen — a participant's own entry/referral/win summary.
Reachable via /profile.

Not yet available: summarizing a user's entries/referrals/wins needs
repository queries that don't exist yet (see
bot/services/user_service.py::get_profile_summary). Until that exists,
this holds a single honest placeholder rather than a dead command —
see bot/keyboards/user_kb.py::menu_only_kb.
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.keyboards.user_kb import menu_only_kb

router = Router(name="user_profile")

_COMING_SOON = "👤 <b>Profile</b>\n\nYour stats will appear here soon."


@router.message(Command("profile"))
async def show_profile(message: Message) -> None:
    """Entry point for the Profile screen."""
    await message.answer(_COMING_SOON, reply_markup=menu_only_kb())
