"""
Admin settings screen: default required channels, editable message
templates, admin list management.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot.keyboards.admin_kb import admin_root_menu_kb

router = Router(name="admin_settings")

_COMING_SOON = "⚙️ <b>Settings</b>\n\nSettings management is coming soon."


@router.callback_query(F.data == "admin:settings")
async def show_settings(callback: CallbackQuery) -> None:
    """Renders the settings menu."""
    # TODO: render current key/value settings (bot/db/repositories, settings table)
    await callback.message.edit_text(_COMING_SOON, reply_markup=admin_root_menu_kb())
    await callback.answer()
