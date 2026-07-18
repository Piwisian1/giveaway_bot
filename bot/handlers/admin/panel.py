"""
Admin panel root.

The ONLY admin command is /admin — every action after that is driven by
inline keyboard callbacks, per the "no command-heavy UX" requirement.
Access is restricted by AdminGuardMiddleware before these handlers ever
run.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from bot.keyboards.admin_kb import admin_root_menu_kb
from bot.texts.en import ADMIN_MENU

router = Router(name="admin_panel")


@router.message(Command("admin"))
async def open_admin_panel(message: Message, state: FSMContext) -> None:
    """
    Entry point into the Telegram-native admin panel. Clears any
    leftover FSM state so re-sending /admin always recovers cleanly
    from a wizard the admin abandoned mid-flow.
    """
    await state.clear()
    await message.answer(ADMIN_MENU, reply_markup=admin_root_menu_kb())


@router.callback_query(F.data == "admin:menu")
async def show_admin_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Re-renders the root admin menu (used by 'Back' buttons), clearing any leftover FSM state."""
    await state.clear()
    await callback.message.edit_text(ADMIN_MENU, reply_markup=admin_root_menu_kb())
    await callback.answer()
