"""
Main menu navigation — the hub users return to from any screen — plus
the Rules screen, which is really just a satellite of that hub (it has
no state of its own beyond whether this visitor has already entered).

Renders the currently active giveaway's card (see
bot/formatters/giveaway_card.py) with its inline keyboard (see
bot/handlers/user/start.py for the initial /start render).
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot.db.connection import get_connection
from bot.db.repositories.entry_repo import EntryRepository
from bot.db.repositories.giveaway_repo import GiveawayRepository
from bot.db.repositories.required_channel_repo import RequiredChannelRepository
from bot.db.repositories.user_repo import UserRepository
from bot.formatters.giveaway_card import render_active_giveaway
from bot.formatters.rules_card import RULES_TEXT
from bot.keyboards.user_kb import main_menu_kb, rules_kb
from bot.services.entry_service import EntryService
from bot.services.giveaway_service import GiveawayService
from bot.services.required_channel_service import RequiredChannelService

router = Router(name="user_menu")


@router.callback_query(F.data == "menu:main")
async def show_main_menu(callback: CallbackQuery) -> None:
    """Re-renders the main menu, e.g. when a user taps a 'Back' button."""
    connection = get_connection()
    giveaway = await GiveawayService(GiveawayRepository(connection)).get_active()
    channels = await RequiredChannelService(RequiredChannelRepository(connection)).get_active_channels()
    await callback.message.edit_text(
        render_active_giveaway(giveaway, len(channels)), reply_markup=main_menu_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "menu:rules")
async def show_rules(callback: CallbackQuery) -> None:
    """
    Shows the Rules screen. Join Giveaway only appears if this visitor
    hasn't entered the active giveaway yet — someone already entered
    doesn't need a second way to do the same thing.
    """
    connection = get_connection()
    giveaway = await GiveawayService(GiveawayRepository(connection)).get_active()

    already_entered = False
    if giveaway is not None:
        user = await UserRepository(connection).get_by_telegram_id(callback.from_user.id)
        if user is not None:
            already_entered = await EntryService(EntryRepository(connection)).has_entered(giveaway.id, user.id)

    show_join = giveaway is not None and not already_entered
    await callback.message.edit_text(RULES_TEXT, reply_markup=rules_kb(show_join))
    await callback.answer()
