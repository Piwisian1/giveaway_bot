"""
Admin user management: search a user, view their history, ban/unban.
All entry points are inline buttons; the search query itself is the
only free-text input required (captured via a short-lived FSM state).
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.keyboards.admin_kb import admin_root_menu_kb

router = Router(name="admin_users")

_COMING_SOON = "👥 <b>Users</b>\n\nUser search and moderation are coming soon."
_NOT_YET_AVAILABLE = "Not yet available."


@router.callback_query(F.data == "admin:users:search")
async def prompt_user_search(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompts the admin to send a telegram_id or @username to look up."""
    # TODO: set FSM state awaiting a search query
    await callback.message.edit_text(_COMING_SOON, reply_markup=admin_root_menu_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("admin:users:ban:"))
async def ban_user(callback: CallbackQuery) -> None:
    """Bans a user, logs the action."""
    # TODO: call user_service.ban(...), which also writes to admin_logs
    await callback.answer(_NOT_YET_AVAILABLE, show_alert=True)


@router.callback_query(F.data.startswith("admin:users:unban:"))
async def unban_user(callback: CallbackQuery) -> None:
    """Unbans a user, logs the action."""
    # TODO: call user_service.unban(...), which also writes to admin_logs
    await callback.answer(_NOT_YET_AVAILABLE, show_alert=True)
