"""
FSM state groups for the admin giveaway-management flow
(bot/handlers/admin/giveaways.py).
"""

from aiogram.fsm.state import State, StatesGroup


class GiveawayCreate(StatesGroup):
    """
    Step-by-step prompts for creating a new giveaway. start_at/end_at
    are not states here — once bonus_prize is captured, control hands
    off to DateTimePicker below (see
    bot/handlers/admin/datetime_picker.py::begin_picker_from_message),
    which returns to GiveawayService.create() only once both dates (or
    a skipped start_at) are fully picked.
    """

    title = State()
    description = State()
    first_prize = State()
    second_prize = State()
    third_prize = State()
    bonus_prize = State()


class GiveawayEditField(StatesGroup):
    """Awaiting a new value for a single non-date field on an existing giveaway."""

    waiting_for_value = State()


class DateTimePicker(StatesGroup):
    """
    Shared inline calendar/hour/minute picker for start_at/end_at, used
    by both the creation wizard and the edit-a-single-field flow — see
    bot/handlers/admin/datetime_picker.py. FSM data (flow/field/
    giveaway_id/cancel_target/cal_year/cal_month/picked_day/picked_hour)
    carries the picker's context; these three states just track which
    screen is currently shown.
    """

    calendar = State()
    hour = State()
    minute = State()
