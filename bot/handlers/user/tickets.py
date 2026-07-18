"""
"My Tickets" — shows every giveaway the current user has entered, their
ticket count per giveaway, and each giveaway's status.

Not yet available: listing a user's entries needs a repository query
that doesn't exist yet (see bot/services/entry_service.py::list_entries_for_user).
Until that exists, this holds a single honest placeholder rather than a
dead screen — see bot/keyboards/user_kb.py::menu_only_kb. Reachable via
/tickets, mirroring bot/handlers/user/profile.py's exact pattern.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.keyboards.user_kb import menu_only_kb

router = Router(name="user_tickets")

_COMING_SOON = "🎟 <b>My Tickets</b>\n\nYour entries will appear here soon."


@router.message(Command("tickets"))
async def show_my_tickets_command(message: Message) -> None:
    """Entry point for the My Tickets screen."""
    await message.answer(_COMING_SOON, reply_markup=menu_only_kb())


@router.callback_query(F.data == "menu:my_tickets")
async def show_my_tickets(callback: CallbackQuery) -> None:
    """Shows a placeholder until entry listing is implemented."""
    await callback.message.edit_text(_COMING_SOON, reply_markup=menu_only_kb())
    await callback.answer()
