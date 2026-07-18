"""
Admin screen for managing the global required-channels list (the same
list rendered to users on the Participate screen — see
bot/handlers/user/participate.py). Every list read here goes straight to
the database, so changes take effect on the Participate screen
immediately, with no bot restart needed.

Does not implement subscription verification itself — see
RequiredChannelService.get_missing_channels for that (already wired into
the Participate screen).
"""

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.db.connection import get_connection
from bot.db.repositories.required_channel_repo import RequiredChannelRepository
from bot.formatters.admin_channels_card import (
    render_admin_channels_screen,
    render_remove_channel_confirm_prompt,
    render_remove_channel_prompt,
)
from bot.keyboards.admin_kb import confirm_action_kb, required_channels_menu_kb, required_channels_remove_kb
from bot.services.required_channel_service import ChannelResolutionError, RequiredChannelService
from bot.states.required_channel_states import RequiredChannelAdd
from bot.texts.en import ADD_CHANNEL_PROMPT, ADD_CHANNEL_SUCCESS

router = Router(name="admin_required_channels")


def _service() -> RequiredChannelService:
    return RequiredChannelService(RequiredChannelRepository(get_connection()))


@router.callback_query(F.data == "admin:required_channels")
async def show_required_channels(callback: CallbackQuery, state: FSMContext) -> None:
    """Renders the active required channels plus Add/Remove/Back."""
    await state.clear()
    channels = await _service().get_active_channels()
    await callback.message.edit_text(
        render_admin_channels_screen(channels),
        reply_markup=required_channels_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:required_channels:add")
async def start_add_channel(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompts the admin for a channel username/link, awaiting a text reply."""
    await state.set_state(RequiredChannelAdd.waiting_for_channel)
    await callback.message.edit_text(ADD_CHANNEL_PROMPT, reply_markup=required_channels_menu_kb())
    await callback.answer()


@router.message(RequiredChannelAdd.waiting_for_channel)
async def receive_channel_input(message: Message, state: FSMContext) -> None:
    """Resolves the submitted username/link and saves it as an active channel."""
    try:
        channel = await _service().add_channel(message.bot, message.text or "")
    except ChannelResolutionError as exc:
        await message.answer(str(exc))
        return

    await state.clear()
    channels = await _service().get_active_channels()
    await message.answer(ADD_CHANNEL_SUCCESS.format(title=channel.title))
    await message.answer(
        render_admin_channels_screen(channels),
        reply_markup=required_channels_menu_kb(),
    )


@router.callback_query(F.data == "admin:required_channels:remove")
async def show_remove_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Lists every configured channel (active or not) as a delete button."""
    await state.clear()
    channels = await _service().list_all_channels()
    await callback.message.edit_text(
        render_remove_channel_prompt(channels),
        reply_markup=required_channels_remove_kb(channels),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:required_channels:remove:(\d+)$"))
async def confirm_remove_channel(callback: CallbackQuery) -> None:
    """Shows a Yes/No confirmation before permanently removing the selected channel."""
    channel_id = int(callback.data.split(":")[-1])
    channel = await _service().get_by_id(channel_id)
    if channel is None:
        await callback.answer("That channel no longer exists.", show_alert=True)
        return
    await callback.message.edit_text(
        render_remove_channel_confirm_prompt(channel),
        reply_markup=confirm_action_kb("admin:required_channels:remove", channel_id),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:required_channels:remove:confirm:(\d+)$"))
async def remove_channel(callback: CallbackQuery) -> None:
    """Deletes the selected channel, then re-renders the active-channels screen."""
    channel_id = int(callback.data.split(":")[-1])
    await _service().remove_channel(channel_id)

    channels = await _service().get_active_channels()
    await callback.message.edit_text(
        render_admin_channels_screen(channels),
        reply_markup=required_channels_menu_kb(),
    )
    await callback.answer("Channel removed.")


@router.callback_query(F.data.regexp(r"^admin:required_channels:remove:cancel:(\d+)$"))
async def cancel_remove_channel(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancels the removal and returns to the remove picker."""
    await show_remove_menu(callback, state)
