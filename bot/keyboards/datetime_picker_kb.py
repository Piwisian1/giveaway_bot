"""
Inline calendar/hour/minute picker keyboards — shared by the giveaway
creation wizard and the edit-a-single-field flow for start_at/end_at
(see bot/handlers/admin/datetime_picker.py). There is no text-entry
fallback: every date/time value comes from tapping one of these
buttons.
"""

import calendar as _calendar
from datetime import date as _date, datetime, timezone

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

_NOOP = "admin:dtpick:noop"


def _today_utc() -> _date:
    return datetime.now(timezone.utc).date()


def build_calendar_kb(
    year: int,
    month: int,
    *,
    allow_skip: bool,
    cancel_target: str,
    selected_day: int | None = None,
) -> InlineKeyboardMarkup:
    """
    Month grid: prev/label/next header, weekday header row, day cells,
    then Skip (if allowed) + Cancel.

    Today is marked with "•"; the already-picked day (if any — only
    meaningful when re-showing this same month after Back from the hour
    grid) is marked with "✅" and takes priority over the "•" mark. Days
    before today are shown (to keep the grid's weekday alignment intact)
    but wired to a no-op — a giveaway can't start or end in the past.
    The prev-month arrow is disabled at the current month for the same
    reason: every day in an earlier month would be a no-op anyway.
    """
    builder = InlineKeyboardBuilder()
    today = _today_utc()

    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    if (year, month) <= (today.year, today.month):
        builder.button(text=" ", callback_data=_NOOP)
    else:
        builder.button(text="‹", callback_data=f"admin:dtpick:nav:{prev_year}:{prev_month}")
    builder.button(text=f"{_calendar.month_name[month]} {year}", callback_data=_NOOP)
    builder.button(text="›", callback_data=f"admin:dtpick:nav:{next_year}:{next_month}")

    for day_name in ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"):
        builder.button(text=day_name, callback_data=_NOOP)

    first_weekday, days_in_month = _calendar.monthrange(year, month)  # first_weekday: 0=Monday
    for _ in range(first_weekday):
        builder.button(text=" ", callback_data=_NOOP)
    for day in range(1, days_in_month + 1):
        cell_date = _date(year, month, day)
        if cell_date < today:
            builder.button(text=f"·{day}", callback_data=_NOOP)
        elif day == selected_day:
            builder.button(text=f"✅{day}", callback_data=f"admin:dtpick:day:{day}")
        elif cell_date == today:
            builder.button(text=f"•{day}", callback_data=f"admin:dtpick:day:{day}")
        else:
            builder.button(text=str(day), callback_data=f"admin:dtpick:day:{day}")

    total_cells = first_weekday + days_in_month
    day_rows = -(-total_cells // 7)  # ceil division

    if allow_skip:
        builder.button(text="⏭ Skip", callback_data="admin:dtpick:skip")
    builder.button(text="❌ Cancel", callback_data=cancel_target)

    builder.adjust(3, 7, *([7] * day_rows), 2 if allow_skip else 1)
    return builder.as_markup()


def build_hour_kb(*, cancel_target: str) -> InlineKeyboardMarkup:
    """24 hours, 6 per row, plus Back (to the calendar) and Cancel."""
    builder = InlineKeyboardBuilder()
    for hour in range(24):
        builder.button(text=f"{hour:02d}", callback_data=f"admin:dtpick:hour:{hour}")
    builder.button(text="🔙 Back", callback_data="admin:dtpick:hour:back")
    builder.button(text="❌ Cancel", callback_data=cancel_target)
    builder.adjust(6, 6, 6, 6, 2)
    return builder.as_markup()


def build_minute_kb(*, cancel_target: str) -> InlineKeyboardMarkup:
    """Minutes at 5-minute intervals, 4 per row, plus Back (to the hour grid) and Cancel."""
    builder = InlineKeyboardBuilder()
    for minute in range(0, 60, 5):
        builder.button(text=f"{minute:02d}", callback_data=f"admin:dtpick:minute:{minute}")
    builder.button(text="🔙 Back", callback_data="admin:dtpick:minute:back")
    builder.button(text="❌ Cancel", callback_data=cancel_target)
    builder.adjust(4, 4, 4, 2)
    return builder.as_markup()
