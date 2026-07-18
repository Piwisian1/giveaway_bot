"""
Admin management of existing giveaways: list by status, view entrants,
force-end, cancel, reroll winners. Entirely inline-menu driven.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot.db.connection import DatabaseConnection, get_connection
from bot.db.repositories.entry_repo import EntryRepository
from bot.db.repositories.giveaway_repo import GiveawayRepository
from bot.db.repositories.required_channel_repo import RequiredChannelRepository
from bot.db.repositories.user_repo import UserRepository
from bot.db.repositories.winner_repo import WinnerRepository
from bot.formatters.admin_giveaway_manage_card import (
    render_cancel_confirm_prompt,
    render_end_confirm_prompt,
    render_entrants_screen,
    render_giveaway_manage_screen,
    render_manage_list_screen,
    render_reroll_confirm_prompt,
)
from bot.keyboards.admin_kb import (
    confirm_action_kb,
    giveaway_list_kb,
    giveaway_manage_back_kb,
    giveaway_manage_kb,
)
from bot.services.entry_service import EntryService
from bot.services.giveaway_service import GiveawayService, derive_status
from bot.services.required_channel_service import RequiredChannelService
from bot.services.winner_service import GiveawayAlreadyClosedError, WinnerService
from bot.texts.en import (
    GIVEAWAY_CANCEL_SUCCESS,
    GIVEAWAY_END_NO_WINNERS,
    GIVEAWAY_END_SUCCESS,
    GIVEAWAY_NOT_ACTIVE_ERROR,
    GIVEAWAY_NOT_ENDED_ERROR,
    GIVEAWAY_REROLL_NO_WINNERS,
    GIVEAWAY_REROLL_SUCCESS,
)

router = Router(name="admin_giveaway_manage")

_NOT_FOUND_ALERT = "That giveaway no longer exists."


def _giveaway_service(connection: DatabaseConnection) -> GiveawayService:
    return GiveawayService(GiveawayRepository(connection))


def _entry_service(connection: DatabaseConnection) -> EntryService:
    return EntryService(EntryRepository(connection))


def _winner_service(connection: DatabaseConnection) -> WinnerService:
    return WinnerService(
        WinnerRepository(connection),
        EntryRepository(connection),
        GiveawayRepository(connection),
        UserRepository(connection),
        RequiredChannelService(RequiredChannelRepository(connection)),
    )


async def _render_manage_screen(callback: CallbackQuery, giveaway_id: int) -> None:
    """Re-renders a single giveaway's management screen. Used both as the initial
    view and to refresh in place after every lifecycle action below."""
    connection = get_connection()
    giveaway = await _giveaway_service(connection).get_by_id(giveaway_id)
    if giveaway is None:
        await callback.answer(_NOT_FOUND_ALERT, show_alert=True)
        return

    winner_repo = WinnerRepository(connection)
    winners = await winner_repo.list_for_giveaway(giveaway_id)

    user_repo = UserRepository(connection)
    winner_users = {}
    for winner in winners:
        user = await user_repo.get_by_id(winner.user_id)
        if user is not None:
            winner_users[winner.user_id] = user

    participant_count = await _entry_service(connection).count_participants(giveaway_id)
    status = derive_status(giveaway, bool(winners))

    await callback.message.edit_text(
        render_giveaway_manage_screen(giveaway, winners, winner_users, participant_count),
        reply_markup=giveaway_manage_kb(giveaway_id, status),
    )


@router.callback_query(F.data == "admin:giveaway:list")
async def list_giveaways(callback: CallbackQuery) -> None:
    """Lists every giveaway with a status marker."""
    connection = get_connection()
    giveaways = await _giveaway_service(connection).list_all()
    winner_repo = WinnerRepository(connection)
    has_winners = {
        giveaway.id: bool(await winner_repo.list_for_giveaway(giveaway.id)) for giveaway in giveaways
    }
    await callback.message.edit_text(
        render_manage_list_screen(giveaways, has_winners),
        reply_markup=giveaway_list_kb(giveaways),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:giveaway:manage:(\d+)$"))
async def manage_giveaway(callback: CallbackQuery) -> None:
    """Shows management actions for a single giveaway."""
    giveaway_id = int(callback.data.split(":")[-1])
    await _render_manage_screen(callback, giveaway_id)
    await callback.answer()


# ------------------------------------------------------------------- End


@router.callback_query(F.data.regexp(r"^admin:giveaway:end:(\d+)$"))
async def confirm_end_giveaway(callback: CallbackQuery) -> None:
    """Shows a Yes/No confirmation before ending the giveaway and drawing winners."""
    giveaway_id = int(callback.data.split(":")[-1])
    giveaway = await _giveaway_service(get_connection()).get_by_id(giveaway_id)
    if giveaway is None:
        await callback.answer(_NOT_FOUND_ALERT, show_alert=True)
        return
    if not giveaway.is_active:
        await callback.answer(GIVEAWAY_NOT_ACTIVE_ERROR, show_alert=True)
        return
    await callback.message.edit_text(
        render_end_confirm_prompt(giveaway),
        reply_markup=confirm_action_kb("admin:giveaway:end", giveaway_id),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:giveaway:end:confirm:(\d+)$"))
async def force_end_giveaway(callback: CallbackQuery) -> None:
    """Force-ends a giveaway immediately and draws winners from current entrants."""
    giveaway_id = int(callback.data.split(":")[-1])
    connection = get_connection()
    giveaway = await _giveaway_service(connection).get_by_id(giveaway_id)
    if giveaway is None:
        await callback.answer(_NOT_FOUND_ALERT, show_alert=True)
        return
    if not giveaway.is_active:
        await callback.answer(GIVEAWAY_NOT_ACTIVE_ERROR, show_alert=True)
        await _render_manage_screen(callback, giveaway_id)
        return

    try:
        winners = await _winner_service(connection).draw(callback.bot, giveaway_id)
    except GiveawayAlreadyClosedError:
        # Lost a race with the auto-closer (or another admin) — it's
        # already been drawn/closed, nothing more to do here.
        await callback.answer(GIVEAWAY_NOT_ACTIVE_ERROR, show_alert=True)
        await _render_manage_screen(callback, giveaway_id)
        return

    await _render_manage_screen(callback, giveaway_id)
    if winners:
        await callback.answer(GIVEAWAY_END_SUCCESS.format(title=giveaway.title, count=len(winners)))
    else:
        await callback.answer(GIVEAWAY_END_NO_WINNERS.format(title=giveaway.title))


@router.callback_query(F.data.regexp(r"^admin:giveaway:end:cancel:(\d+)$"))
async def cancel_confirm_end_giveaway(callback: CallbackQuery) -> None:
    """Cancels the End confirmation and returns to the management screen."""
    giveaway_id = int(callback.data.split(":")[-1])
    await _render_manage_screen(callback, giveaway_id)
    await callback.answer()


# ---------------------------------------------------------------- Cancel


@router.callback_query(F.data.regexp(r"^admin:giveaway:cancel:(\d+)$"))
async def confirm_cancel_giveaway(callback: CallbackQuery) -> None:
    """Shows a Yes/No confirmation before cancelling the giveaway without drawing winners."""
    giveaway_id = int(callback.data.split(":")[-1])
    giveaway = await _giveaway_service(get_connection()).get_by_id(giveaway_id)
    if giveaway is None:
        await callback.answer(_NOT_FOUND_ALERT, show_alert=True)
        return
    if not giveaway.is_active:
        await callback.answer(GIVEAWAY_NOT_ACTIVE_ERROR, show_alert=True)
        return
    await callback.message.edit_text(
        render_cancel_confirm_prompt(giveaway),
        reply_markup=confirm_action_kb("admin:giveaway:cancel", giveaway_id),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:giveaway:cancel:confirm:(\d+)$"))
async def cancel_giveaway(callback: CallbackQuery) -> None:
    """Cancels a giveaway without drawing winners."""
    giveaway_id = int(callback.data.split(":")[-1])
    connection = get_connection()
    service = _giveaway_service(connection)
    giveaway = await service.get_by_id(giveaway_id)
    if giveaway is None:
        await callback.answer(_NOT_FOUND_ALERT, show_alert=True)
        return
    if not giveaway.is_active:
        await callback.answer(GIVEAWAY_NOT_ACTIVE_ERROR, show_alert=True)
        await _render_manage_screen(callback, giveaway_id)
        return

    await service.deactivate(giveaway_id)
    await _render_manage_screen(callback, giveaway_id)
    await callback.answer(GIVEAWAY_CANCEL_SUCCESS.format(title=giveaway.title))


@router.callback_query(F.data.regexp(r"^admin:giveaway:cancel:cancel:(\d+)$"))
async def cancel_confirm_cancel_giveaway(callback: CallbackQuery) -> None:
    """Cancels the Cancel confirmation and returns to the management screen."""
    giveaway_id = int(callback.data.split(":")[-1])
    await _render_manage_screen(callback, giveaway_id)
    await callback.answer()


# ---------------------------------------------------------------- Reroll


@router.callback_query(F.data.regexp(r"^admin:giveaway:reroll:(\d+)$"))
async def confirm_reroll_winners(callback: CallbackQuery) -> None:
    """Shows a Yes/No confirmation before rerolling winners for an already-ended giveaway."""
    giveaway_id = int(callback.data.split(":")[-1])
    connection = get_connection()
    giveaway = await _giveaway_service(connection).get_by_id(giveaway_id)
    if giveaway is None:
        await callback.answer(_NOT_FOUND_ALERT, show_alert=True)
        return
    has_winners = bool(await WinnerRepository(connection).list_for_giveaway(giveaway_id))
    if giveaway.is_active or not has_winners:
        await callback.answer(GIVEAWAY_NOT_ENDED_ERROR, show_alert=True)
        return
    await callback.message.edit_text(
        render_reroll_confirm_prompt(giveaway),
        reply_markup=confirm_action_kb("admin:giveaway:reroll", giveaway_id),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:giveaway:reroll:confirm:(\d+)$"))
async def reroll_winners(callback: CallbackQuery) -> None:
    """Re-draws winners for an already-ended giveaway, excluding previous winners."""
    giveaway_id = int(callback.data.split(":")[-1])
    connection = get_connection()
    giveaway = await _giveaway_service(connection).get_by_id(giveaway_id)
    if giveaway is None:
        await callback.answer(_NOT_FOUND_ALERT, show_alert=True)
        return
    has_winners = bool(await WinnerRepository(connection).list_for_giveaway(giveaway_id))
    if giveaway.is_active or not has_winners:
        await callback.answer(GIVEAWAY_NOT_ENDED_ERROR, show_alert=True)
        await _render_manage_screen(callback, giveaway_id)
        return

    winners = await _winner_service(connection).reroll(callback.bot, giveaway_id)
    await _render_manage_screen(callback, giveaway_id)
    if winners:
        await callback.answer(GIVEAWAY_REROLL_SUCCESS.format(count=len(winners)))
    else:
        await callback.answer(GIVEAWAY_REROLL_NO_WINNERS)


@router.callback_query(F.data.regexp(r"^admin:giveaway:reroll:cancel:(\d+)$"))
async def cancel_confirm_reroll_winners(callback: CallbackQuery) -> None:
    """Cancels the Reroll confirmation and returns to the management screen."""
    giveaway_id = int(callback.data.split(":")[-1])
    await _render_manage_screen(callback, giveaway_id)
    await callback.answer()


# -------------------------------------------------------------- Entrants


@router.callback_query(F.data.regexp(r"^admin:giveaway:entrants:(\d+)$"))
async def view_entrants(callback: CallbackQuery) -> None:
    """Shows the entrant count for a giveaway."""
    giveaway_id = int(callback.data.split(":")[-1])
    connection = get_connection()
    giveaway = await _giveaway_service(connection).get_by_id(giveaway_id)
    if giveaway is None:
        await callback.answer(_NOT_FOUND_ALERT, show_alert=True)
        return
    participant_count = await _entry_service(connection).count_participants(giveaway_id)
    await callback.message.edit_text(
        render_entrants_screen(giveaway, participant_count),
        reply_markup=giveaway_manage_back_kb(giveaway_id),
    )
    await callback.answer()
