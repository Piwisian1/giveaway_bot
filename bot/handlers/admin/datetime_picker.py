"""
Shared inline date/time picker (calendar -> hour -> minute) used by both
the giveaway creation wizard and the single-field edit flow for
start_at/end_at — see bot/handlers/admin/giveaways.py, which hands off
to begin_picker_from_message()/begin_picker_from_callback() and never
falls back to typed text for a date field.

All dates are UTC, matching the storage format used everywhere else
(GiveawayRepository, the auto-closer's datetime('now') comparisons).
The calendar always opens on the current UTC month. FSM data carries
the picker's context (flow/field/giveaway_id/cancel_target plus the
in-progress cal_year/cal_month/picked_day/picked_hour); the three
DateTimePicker states just track which screen is currently shown.
"""

from __future__ import annotations

from datetime import datetime, timezone

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.db.connection import get_connection
from bot.db.repositories.giveaway_repo import GiveawayRepository
from bot.formatters.admin_giveaways_card import field_label, render_giveaway_edit_screen, render_giveaways_screen
from bot.keyboards.admin_kb import giveaway_edit_fields_kb, giveaways_menu_kb
from bot.keyboards.datetime_picker_kb import build_calendar_kb, build_hour_kb, build_minute_kb
from bot.services.giveaway_service import GiveawayService
from bot.states.giveaway_states import DateTimePicker
from bot.texts.en import (
    DATETIME_PICK_CALENDAR_CAPTION,
    DATETIME_PICK_HOUR_CAPTION,
    DATETIME_PICK_MINUTE_CAPTION,
    DATETIME_PICK_USE_BUTTONS,
    GIVEAWAY_CREATE_SUCCESS,
    GIVEAWAY_EDIT_SUCCESS,
)

router = Router(name="admin_datetime_picker")

_STORAGE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _service() -> GiveawayService:
    return GiveawayService(GiveawayRepository(get_connection()))


async def _init_picker_data(
    state: FSMContext,
    *,
    flow: str,
    field: str,
    allow_skip: bool,
    giveaway_id: int | None,
    cancel_target: str,
) -> tuple[int, int]:
    now = datetime.now(timezone.utc)
    await state.update_data(
        flow=flow,
        field=field,
        allow_skip=allow_skip,
        giveaway_id=giveaway_id,
        cancel_target=cancel_target,
        cal_year=now.year,
        cal_month=now.month,
        # Reset explicitly — update_data() merges rather than replaces,
        # so without this a day/hour picked for a *previous* field (e.g.
        # start_at) would still be sitting in FSM data and wrongly show
        # as "selected" the moment this fresh picker (e.g. end_at) opens.
        picked_day=None,
        picked_hour=None,
    )
    await state.set_state(DateTimePicker.calendar)
    return now.year, now.month


async def begin_picker_from_message(
    message: Message,
    state: FSMContext,
    *,
    flow: str,
    field: str,
    allow_skip: bool,
    giveaway_id: int | None = None,
    cancel_target: str,
) -> None:
    """
    Entry point for the ONE call site that doesn't already have a bot
    message to edit in place: the creation wizard's bonus_prize step,
    which receives a plain text reply and must send a fresh message to
    show the calendar.
    """
    year, month = await _init_picker_data(
        state, flow=flow, field=field, allow_skip=allow_skip, giveaway_id=giveaway_id, cancel_target=cancel_target
    )
    await message.answer(
        DATETIME_PICK_CALENDAR_CAPTION.format(field=field_label(field)),
        reply_markup=build_calendar_kb(year, month, allow_skip=allow_skip, cancel_target=cancel_target),
    )


async def begin_picker_from_callback(
    callback: CallbackQuery,
    state: FSMContext,
    *,
    flow: str,
    field: str,
    allow_skip: bool,
    giveaway_id: int | None = None,
    cancel_target: str,
) -> None:
    """
    Entry point for every other call site — the edit flow's
    start_edit_field, and this module's own start_at -> end_at handoff
    mid-wizard — all of which already have a bot message to edit in
    place rather than sending a new one.
    """
    year, month = await _init_picker_data(
        state, flow=flow, field=field, allow_skip=allow_skip, giveaway_id=giveaway_id, cancel_target=cancel_target
    )
    await callback.message.edit_text(
        DATETIME_PICK_CALENDAR_CAPTION.format(field=field_label(field)),
        reply_markup=build_calendar_kb(year, month, allow_skip=allow_skip, cancel_target=cancel_target),
    )


async def _rerender_calendar(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await callback.message.edit_text(
        DATETIME_PICK_CALENDAR_CAPTION.format(field=field_label(data["field"])),
        reply_markup=build_calendar_kb(
            data["cal_year"],
            data["cal_month"],
            allow_skip=data["allow_skip"],
            cancel_target=data["cancel_target"],
            selected_day=data.get("picked_day"),
        ),
    )


@router.callback_query(DateTimePicker.calendar, F.data == "admin:dtpick:noop")
async def noop(callback: CallbackQuery) -> None:
    """Inert header cells (weekday names, the month/year label)."""
    await callback.answer()


@router.callback_query(DateTimePicker.calendar, F.data.regexp(r"^admin:dtpick:nav:(\d+):(\d+)$"))
async def navigate_month(callback: CallbackQuery, state: FSMContext) -> None:
    """Moves the calendar to a different month without picking a day."""
    _, _, _, year, month = callback.data.split(":")
    # Clears any previously-picked day — it belonged to the month we're
    # navigating away from, so keeping it would wrongly highlight that
    # same day number in the new month.
    await state.update_data(cal_year=int(year), cal_month=int(month), picked_day=None)
    await _rerender_calendar(callback, state)
    await callback.answer()


@router.callback_query(DateTimePicker.calendar, F.data == "admin:dtpick:skip")
async def skip_field(callback: CallbackQuery, state: FSMContext) -> None:
    """Skips this (optional) field entirely — only ever offered for start_at."""
    await _finalize(callback, state, value=None)


@router.callback_query(DateTimePicker.calendar, F.data.regexp(r"^admin:dtpick:day:(\d+)$"))
async def pick_day(callback: CallbackQuery, state: FSMContext) -> None:
    """Records the picked day, advances to the hour grid."""
    day = int(callback.data.split(":")[-1])
    await state.update_data(picked_day=day)
    await state.set_state(DateTimePicker.hour)
    data = await state.get_data()
    date_str = f"{data['cal_year']:04d}-{data['cal_month']:02d}-{day:02d}"
    await callback.message.edit_text(
        DATETIME_PICK_HOUR_CAPTION.format(date=date_str),
        reply_markup=build_hour_kb(cancel_target=data["cancel_target"]),
    )
    await callback.answer()


@router.callback_query(DateTimePicker.hour, F.data == "admin:dtpick:hour:back")
async def hour_back(callback: CallbackQuery, state: FSMContext) -> None:
    """Returns to the calendar without losing the current month position."""
    await state.set_state(DateTimePicker.calendar)
    await _rerender_calendar(callback, state)
    await callback.answer()


@router.callback_query(DateTimePicker.hour, F.data.regexp(r"^admin:dtpick:hour:(\d+)$"))
async def pick_hour(callback: CallbackQuery, state: FSMContext) -> None:
    """Records the picked hour, advances to the minute grid."""
    hour = int(callback.data.split(":")[-1])
    await state.update_data(picked_hour=hour)
    await state.set_state(DateTimePicker.minute)
    data = await state.get_data()
    date_str = f"{data['cal_year']:04d}-{data['cal_month']:02d}-{data['picked_day']:02d}"
    await callback.message.edit_text(
        DATETIME_PICK_MINUTE_CAPTION.format(date=date_str, hour=f"{hour:02d}"),
        reply_markup=build_minute_kb(cancel_target=data["cancel_target"]),
    )
    await callback.answer()


@router.callback_query(DateTimePicker.minute, F.data == "admin:dtpick:minute:back")
async def minute_back(callback: CallbackQuery, state: FSMContext) -> None:
    """Returns to the hour grid for the already-picked day."""
    data = await state.get_data()
    await state.set_state(DateTimePicker.hour)
    date_str = f"{data['cal_year']:04d}-{data['cal_month']:02d}-{data['picked_day']:02d}"
    await callback.message.edit_text(
        DATETIME_PICK_HOUR_CAPTION.format(date=date_str),
        reply_markup=build_hour_kb(cancel_target=data["cancel_target"]),
    )
    await callback.answer()


@router.callback_query(DateTimePicker.minute, F.data.regexp(r"^admin:dtpick:minute:(\d+)$"))
async def pick_minute(callback: CallbackQuery, state: FSMContext) -> None:
    """Records the picked minute — the date/time is now fully specified."""
    minute = int(callback.data.split(":")[-1])
    data = await state.get_data()
    value = datetime(
        data["cal_year"], data["cal_month"], data["picked_day"], data["picked_hour"], minute
    ).strftime(_STORAGE_FORMAT)
    await _finalize(callback, state, value=value)


@router.message(StateFilter(DateTimePicker.calendar, DateTimePicker.hour, DateTimePicker.minute))
async def reject_typed_input(message: Message) -> None:
    """The picker is buttons-only — a typed reply here is never parsed as a date."""
    await message.answer(DATETIME_PICK_USE_BUTTONS)


async def _finalize(callback: CallbackQuery, state: FSMContext, value: str | None) -> None:
    """
    `value` is a fully-formatted 'YYYY-MM-DD HH:MM:SS' string, or None if
    the field was skipped (only possible for start_at). Resumes whichever
    flow started the picker.
    """
    data = await state.get_data()
    flow = data["flow"]
    field = data["field"]

    if flow == "create":
        await state.update_data(**{field: value})
        if field == "start_at":
            await begin_picker_from_callback(
                callback,
                state,
                flow="create",
                field="end_at",
                allow_skip=False,
                cancel_target=data["cancel_target"],
            )
            await callback.answer()
            return

        wizard_data = await state.get_data()
        await state.clear()
        giveaway = await _service().create(wizard_data)
        await callback.message.edit_text(GIVEAWAY_CREATE_SUCCESS.format(title=giveaway.title))
        giveaways = await _service().list_all()
        await callback.message.answer(render_giveaways_screen(giveaways), reply_markup=giveaways_menu_kb())
        await callback.answer()
        return

    # flow == "edit"
    giveaway_id = data["giveaway_id"]
    await _service().update_field(giveaway_id, field, value)
    await state.clear()
    await callback.message.edit_text(GIVEAWAY_EDIT_SUCCESS.format(field=field_label(field)))
    giveaway = await _service().get_by_id(giveaway_id)
    if giveaway is not None:
        await callback.message.answer(
            render_giveaway_edit_screen(giveaway),
            reply_markup=giveaway_edit_fields_kb(giveaway_id),
        )
    await callback.answer()
