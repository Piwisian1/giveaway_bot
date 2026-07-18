"""
Admin "🎁 Giveaway" management: create, edit, delete, and activate.

Only one giveaway can be active at a time (see Giveaway's docstring in
bot/db/models.py) — activating one deactivates whichever was active
before. The /start and Participate screens always read the active
giveaway live from the database (see bot/handlers/user/start.py,
bot/handlers/user/menu.py), so changes here take effect immediately,
with no bot restart needed.

Does not implement participant registration or winner selection.
"""

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.db.connection import get_connection
from bot.db.repositories.giveaway_repo import GiveawayRepository
from bot.db.repositories.winner_repo import WinnerRepository
from bot.formatters.admin_giveaways_card import (
    field_label,
    render_delete_confirm_prompt,
    render_giveaway_edit_screen,
    render_giveaways_screen,
    render_pick_giveaway_prompt,
)
from bot.handlers.admin.datetime_picker import begin_picker_from_callback, begin_picker_from_message
from bot.keyboards.admin_kb import (
    admin_cancel_kb,
    confirm_action_kb,
    giveaway_edit_fields_kb,
    giveaways_menu_kb,
    giveaways_pick_kb,
)
from bot.services.giveaway_service import GiveawayService
from bot.states.giveaway_states import GiveawayCreate, GiveawayEditField
from bot.texts.en import (
    GIVEAWAY_ACTIVATE_SUCCESS,
    GIVEAWAY_ALREADY_DRAWN_ERROR,
    GIVEAWAY_CREATE_PROMPTS,
    GIVEAWAY_DELETE_SUCCESS,
    GIVEAWAY_EDIT_FIELD_PROMPT,
    GIVEAWAY_EDIT_REQUIRED_FIELD_PROMPT,
    GIVEAWAY_EDIT_SUCCESS,
    GIVEAWAY_REQUIRED_FIELD_ERROR,
)

router = Router(name="admin_giveaways")

_DATE_FIELDS = {"start_at", "end_at"}
# Same fields the creation wizard requires (see set_title/set_first_prize/
# datetime_picker.py's create+end_at finalization) — the edit flow must
# not let an admin blank these back out afterward. Clearing first_prize
# would leave 0 prize tiers to draw (see
# bot/services/winner_service.py::_prize_tiers); clearing end_at would
# make the giveaway invisible to the auto-closer forever (see
# GiveawayRepository.list_due_for_close).
_REQUIRED_FIELDS = {"title", "first_prize", "end_at"}

# Cancelling the creation wizard abandons all progress and returns to
# the giveaway list — show_giveaways_screen already clears FSM state.
_WIZARD_CANCEL_KB = admin_cancel_kb("admin:giveaways")
_WIZARD_CANCEL_TARGET = "admin:giveaways"


def _service() -> GiveawayService:
    return GiveawayService(GiveawayRepository(get_connection()))


def _parse_optional(text: str | None) -> str | None:
    """Blank input or a bare "-" means "skip"/"clear"."""
    value = (text or "").strip()
    return None if value in ("", "-") else value


@router.callback_query(F.data == "admin:giveaways")
async def show_giveaways_screen(callback: CallbackQuery, state: FSMContext) -> None:
    """Renders every giveaway plus Create/Edit/Delete/Activate/Back."""
    await state.clear()
    giveaways = await _service().list_all()
    await callback.message.edit_text(
        render_giveaways_screen(giveaways),
        reply_markup=giveaways_menu_kb(),
    )
    await callback.answer()


# ---------------------------------------------------------------- Create


@router.callback_query(F.data == "admin:giveaways:create")
async def start_create_wizard(callback: CallbackQuery, state: FSMContext) -> None:
    """Begins the giveaway creation wizard."""
    await state.clear()
    await state.set_state(GiveawayCreate.title)
    await callback.message.edit_text(GIVEAWAY_CREATE_PROMPTS["title"], reply_markup=_WIZARD_CANCEL_KB)
    await callback.answer()


@router.message(GiveawayCreate.title)
async def set_title(message: Message, state: FSMContext) -> None:
    """Captures the title (required), advances to the description step."""
    title = _parse_optional(message.text)
    if title is None:
        await message.answer(GIVEAWAY_REQUIRED_FIELD_ERROR, reply_markup=_WIZARD_CANCEL_KB)
        return
    await state.update_data(title=title)
    await state.set_state(GiveawayCreate.description)
    await message.answer(GIVEAWAY_CREATE_PROMPTS["description"], reply_markup=_WIZARD_CANCEL_KB)


@router.message(GiveawayCreate.description)
async def set_description(message: Message, state: FSMContext) -> None:
    """Captures the optional description, advances to the 1st prize step."""
    await state.update_data(description=_parse_optional(message.text))
    await state.set_state(GiveawayCreate.first_prize)
    await message.answer(GIVEAWAY_CREATE_PROMPTS["first_prize"], reply_markup=_WIZARD_CANCEL_KB)


@router.message(GiveawayCreate.first_prize)
async def set_first_prize(message: Message, state: FSMContext) -> None:
    """Captures the 1st prize (required), advances to the 2nd prize step."""
    first_prize = _parse_optional(message.text)
    if first_prize is None:
        await message.answer(GIVEAWAY_REQUIRED_FIELD_ERROR, reply_markup=_WIZARD_CANCEL_KB)
        return
    await state.update_data(first_prize=first_prize)
    await state.set_state(GiveawayCreate.second_prize)
    await message.answer(GIVEAWAY_CREATE_PROMPTS["second_prize"], reply_markup=_WIZARD_CANCEL_KB)


@router.message(GiveawayCreate.second_prize)
async def set_second_prize(message: Message, state: FSMContext) -> None:
    """Captures the optional 2nd prize, advances to the 3rd prize step."""
    await state.update_data(second_prize=_parse_optional(message.text))
    await state.set_state(GiveawayCreate.third_prize)
    await message.answer(GIVEAWAY_CREATE_PROMPTS["third_prize"], reply_markup=_WIZARD_CANCEL_KB)


@router.message(GiveawayCreate.third_prize)
async def set_third_prize(message: Message, state: FSMContext) -> None:
    """Captures the optional 3rd prize, advances to the bonus prize step."""
    await state.update_data(third_prize=_parse_optional(message.text))
    await state.set_state(GiveawayCreate.bonus_prize)
    await message.answer(GIVEAWAY_CREATE_PROMPTS["bonus_prize"], reply_markup=_WIZARD_CANCEL_KB)


@router.message(GiveawayCreate.bonus_prize)
async def set_bonus_prize(message: Message, state: FSMContext) -> None:
    """Captures the optional bonus prize, then begins the start-date picker."""
    await state.update_data(bonus_prize=_parse_optional(message.text))
    await begin_picker_from_message(
        message,
        state,
        flow="create",
        field="start_at",
        allow_skip=True,
        cancel_target=_WIZARD_CANCEL_TARGET,
    )


# ------------------------------------------------------------------ Edit


@router.callback_query(F.data == "admin:giveaways:edit")
async def show_edit_picker(callback: CallbackQuery, state: FSMContext) -> None:
    """Lists every giveaway to pick one to edit."""
    await state.clear()
    giveaways = await _service().list_all()
    await callback.message.edit_text(
        render_pick_giveaway_prompt("✏️ Edit Giveaway", giveaways),
        reply_markup=giveaways_pick_kb(giveaways, "edit"),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:giveaways:edit:(\d+)$"))
async def show_giveaway_edit_fields(callback: CallbackQuery, state: FSMContext) -> None:
    """Shows the current field values plus a button per editable field."""
    await state.clear()
    giveaway_id = int(callback.data.split(":")[-1])
    giveaway = await _service().get_by_id(giveaway_id)
    if giveaway is None:
        await callback.answer("That giveaway no longer exists.", show_alert=True)
        return
    await callback.message.edit_text(
        render_giveaway_edit_screen(giveaway),
        reply_markup=giveaway_edit_fields_kb(giveaway_id),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:giveaways:edit:(\d+):field:(\w+)$"))
async def start_edit_field(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompts for a new value for the selected field — via the inline
    picker for start_at/end_at, or a text prompt for everything else."""
    _, _, _, giveaway_id, _, field = callback.data.split(":")
    giveaway_id = int(giveaway_id)
    await state.clear()

    if field in _DATE_FIELDS:
        await begin_picker_from_callback(
            callback,
            state,
            flow="edit",
            field=field,
            allow_skip=field not in _REQUIRED_FIELDS,
            giveaway_id=giveaway_id,
            cancel_target=f"admin:giveaways:edit:{giveaway_id}",
        )
        await callback.answer()
        return

    await state.update_data(giveaway_id=giveaway_id, field=field)
    await state.set_state(GiveawayEditField.waiting_for_value)
    cancel_kb = admin_cancel_kb(f"admin:giveaways:edit:{giveaway_id}")
    template = GIVEAWAY_EDIT_REQUIRED_FIELD_PROMPT if field in _REQUIRED_FIELDS else GIVEAWAY_EDIT_FIELD_PROMPT
    prompt = template.format(field=field_label(field))
    await callback.message.edit_text(prompt, reply_markup=cancel_kb)
    await callback.answer()


@router.message(GiveawayEditField.waiting_for_value)
async def receive_edit_value(message: Message, state: FSMContext) -> None:
    """Validates and saves the new value for a non-date field, then re-renders the edit screen."""
    data = await state.get_data()
    giveaway_id = data["giveaway_id"]
    field = data["field"]
    cancel_kb = admin_cancel_kb(f"admin:giveaways:edit:{giveaway_id}")

    value = _parse_optional(message.text)
    if field in _REQUIRED_FIELDS and value is None:
        await message.answer(GIVEAWAY_REQUIRED_FIELD_ERROR, reply_markup=cancel_kb)
        return

    await _service().update_field(giveaway_id, field, value)
    await state.clear()
    await message.answer(GIVEAWAY_EDIT_SUCCESS.format(field=field_label(field)))

    giveaway = await _service().get_by_id(giveaway_id)
    if giveaway is not None:
        await message.answer(
            render_giveaway_edit_screen(giveaway),
            reply_markup=giveaway_edit_fields_kb(giveaway_id),
        )


# ---------------------------------------------------------------- Delete


@router.callback_query(F.data == "admin:giveaways:delete")
async def show_delete_picker(callback: CallbackQuery, state: FSMContext) -> None:
    """Lists every giveaway to pick one to delete."""
    await state.clear()
    giveaways = await _service().list_all()
    await callback.message.edit_text(
        render_pick_giveaway_prompt("🗑 Delete Giveaway", giveaways),
        reply_markup=giveaways_pick_kb(giveaways, "delete"),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:giveaways:delete:(\d+)$"))
async def confirm_delete_giveaway(callback: CallbackQuery) -> None:
    """Shows a Yes/No confirmation before permanently deleting the selected giveaway."""
    giveaway_id = int(callback.data.split(":")[-1])
    giveaway = await _service().get_by_id(giveaway_id)
    if giveaway is None:
        await callback.answer("That giveaway no longer exists.", show_alert=True)
        return
    await callback.message.edit_text(
        render_delete_confirm_prompt(giveaway),
        reply_markup=confirm_action_kb("admin:giveaways:delete", giveaway_id),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:giveaways:delete:confirm:(\d+)$"))
async def delete_giveaway(callback: CallbackQuery) -> None:
    """Deletes the selected giveaway, then re-renders the giveaway list."""
    giveaway_id = int(callback.data.split(":")[-1])
    giveaway = await _service().get_by_id(giveaway_id)
    await _service().delete(giveaway_id)

    giveaways = await _service().list_all()
    await callback.message.edit_text(
        render_giveaways_screen(giveaways),
        reply_markup=giveaways_menu_kb(),
    )
    await callback.answer(
        GIVEAWAY_DELETE_SUCCESS.format(title=giveaway.title) if giveaway else "Deleted."
    )


@router.callback_query(F.data.regexp(r"^admin:giveaways:delete:cancel:(\d+)$"))
async def cancel_delete_giveaway(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancels the deletion and returns to the delete picker."""
    await show_delete_picker(callback, state)


# -------------------------------------------------------------- Activate


@router.callback_query(F.data == "admin:giveaways:activate")
async def show_activate_picker(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Lists every giveaway that can still be (re)activated — excludes any
    giveaway that already had winners drawn, since reactivating one
    would let new users join something that's already been decided.
    """
    await state.clear()
    winner_repo = WinnerRepository(get_connection())
    giveaways = await _service().list_all()
    activatable = [
        giveaway
        for giveaway in giveaways
        if giveaway.is_active or not await winner_repo.list_for_giveaway(giveaway.id)
    ]
    await callback.message.edit_text(
        render_pick_giveaway_prompt("✅ Activate Giveaway", activatable),
        reply_markup=giveaways_pick_kb(activatable, "activate"),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:giveaways:activate:(\d+)$"))
async def activate_giveaway(callback: CallbackQuery) -> None:
    """Activates the selected giveaway, deactivating whichever was active before."""
    giveaway_id = int(callback.data.split(":")[-1])
    connection = get_connection()
    if await WinnerRepository(connection).list_for_giveaway(giveaway_id):
        # The real guard — the picker above already filters these out,
        # but this is the actual correctness boundary regardless of how
        # this callback_data was reached.
        await callback.answer(GIVEAWAY_ALREADY_DRAWN_ERROR, show_alert=True)
        return

    await _service().activate(giveaway_id)
    giveaway = await _service().get_by_id(giveaway_id)

    giveaways = await _service().list_all()
    await callback.message.edit_text(
        render_giveaways_screen(giveaways),
        reply_markup=giveaways_menu_kb(),
    )
    await callback.answer(
        GIVEAWAY_ACTIVATE_SUCCESS.format(title=giveaway.title) if giveaway else "Activated."
    )
