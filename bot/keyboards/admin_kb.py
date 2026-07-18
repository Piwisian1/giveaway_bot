"""
Inline keyboards for the Telegram-native admin panel. Every admin
action after /admin is a callback button — no additional slash
commands.
"""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.db.models import Giveaway, RequiredChannel


def admin_root_menu_kb() -> InlineKeyboardMarkup:
    """Giveaway / Statistics / Users / Settings / Required Channels, in two rows."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🎁 Giveaway", callback_data="admin:giveaways")
    builder.button(text="📊 Statistics", callback_data="admin:stats")
    builder.button(text="👥 Users", callback_data="admin:users:search")
    builder.button(text="⚙️ Settings", callback_data="admin:settings")
    builder.button(text="📢 Required Channels", callback_data="admin:required_channels")
    builder.adjust(3, 2)
    return builder.as_markup()


def admin_cancel_kb(target: str) -> InlineKeyboardMarkup:
    """
    Single Cancel button — the escape hatch attached to every FSM prompt
    (wizard steps, field-edit prompts) so an admin can back out mid-flow
    instead of being stuck typing. `target` is the callback_data of the
    screen to return to; that screen's own handler is responsible for
    clearing the FSM state (every relevant one already does).
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Cancel", callback_data=target)
    return builder.as_markup()


def giveaways_menu_kb() -> InlineKeyboardMarkup:
    """Create / Edit / Delete / Activate / Manage / Back, shown under the giveaway list, in two rows."""
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Create Giveaway", callback_data="admin:giveaways:create")
    builder.button(text="✏️ Edit Giveaway", callback_data="admin:giveaways:edit")
    builder.button(text="🗑 Delete Giveaway", callback_data="admin:giveaways:delete")
    builder.button(text="✅ Activate Giveaway", callback_data="admin:giveaways:activate")
    builder.button(text="📋 Manage Giveaway", callback_data="admin:giveaway:list")
    builder.button(text="🔙 Back", callback_data="admin:menu")
    builder.adjust(3, 3)
    return builder.as_markup()


def giveaways_pick_kb(giveaways: list[Giveaway], action: str) -> InlineKeyboardMarkup:
    """One button per giveaway for the given action (edit/delete/activate), plus Back."""
    builder = InlineKeyboardBuilder()
    for giveaway in giveaways:
        marker = "🟢 " if giveaway.is_active else ""
        builder.button(
            text=f"{marker}{giveaway.title}",
            callback_data=f"admin:giveaways:{action}:{giveaway.id}",
        )
    builder.button(text="🔙 Back", callback_data="admin:giveaways")
    builder.adjust(1)
    return builder.as_markup()


def giveaway_edit_fields_kb(giveaway_id: int) -> InlineKeyboardMarkup:
    """One button per editable field, plus Back to the giveaway list."""
    builder = InlineKeyboardBuilder()
    fields = (
        ("title", "Title"),
        ("description", "Description"),
        ("first_prize", "1st Prize"),
        ("second_prize", "2nd Prize"),
        ("third_prize", "3rd Prize"),
        ("bonus_prize", "Bonus Prize"),
        ("start_at", "Start Date"),
        ("end_at", "End Date"),
    )
    for field, label in fields:
        builder.button(
            text=label,
            callback_data=f"admin:giveaways:edit:{giveaway_id}:field:{field}",
        )
    builder.button(text="🔙 Back", callback_data="admin:giveaways:edit")
    # 8 field buttons (3, 3, 2) then Back alone on its own row.
    builder.adjust(3, 3, 2, 1)
    return builder.as_markup()


def required_channels_menu_kb() -> InlineKeyboardMarkup:
    """Add Channel / Remove Channel / Back, shown under the active-channels list, in two rows."""
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Add Channel", callback_data="admin:required_channels:add")
    builder.button(text="🗑 Remove Channel", callback_data="admin:required_channels:remove")
    builder.button(text="🔙 Back", callback_data="admin:menu")
    builder.adjust(2, 1)
    return builder.as_markup()


def required_channels_remove_kb(channels: list[RequiredChannel]) -> InlineKeyboardMarkup:
    """One delete button per configured channel, plus Back to the Required Channels screen."""
    builder = InlineKeyboardBuilder()
    for channel in channels:
        builder.button(
            text=f"🗑 {channel.title}",
            callback_data=f"admin:required_channels:remove:{channel.id}",
        )
    builder.button(text="🔙 Back", callback_data="admin:required_channels")
    builder.adjust(1)
    return builder.as_markup()


def giveaway_list_kb(giveaways: list[Giveaway]) -> InlineKeyboardMarkup:
    """One button per giveaway, leading to its management screen, plus Back."""
    builder = InlineKeyboardBuilder()
    for giveaway in giveaways:
        marker = "🟢 " if giveaway.is_active else ""
        builder.button(
            text=f"{marker}{giveaway.title}",
            callback_data=f"admin:giveaway:manage:{giveaway.id}",
        )
    builder.button(text="🔙 Back", callback_data="admin:giveaways")
    builder.adjust(1)
    return builder.as_markup()


def giveaway_manage_kb(giveaway_id: int, status: str) -> InlineKeyboardMarkup:
    """
    End & Draw Winners / Cancel (only while active), Reroll Winners
    (only once ended), View Entrants, plus Back. `status` is one of
    "active" / "ended" / "inactive" — see
    bot/services/giveaway_service.py::derive_status.
    """
    builder = InlineKeyboardBuilder()
    if status == "active":
        builder.button(text="🔴 End & Draw Winners", callback_data=f"admin:giveaway:end:{giveaway_id}")
        builder.button(text="🚫 Cancel", callback_data=f"admin:giveaway:cancel:{giveaway_id}")
    elif status == "ended":
        builder.button(text="🔁 Reroll Winners", callback_data=f"admin:giveaway:reroll:{giveaway_id}")
    builder.button(text="👥 View Entrants", callback_data=f"admin:giveaway:entrants:{giveaway_id}")
    builder.button(text="🔙 Back", callback_data="admin:giveaway:list")
    builder.adjust(2, 2)
    return builder.as_markup()


def giveaway_manage_back_kb(giveaway_id: int) -> InlineKeyboardMarkup:
    """Single Back button to a single giveaway's management screen."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Back", callback_data=f"admin:giveaway:manage:{giveaway_id}")
    return builder.as_markup()


def confirm_action_kb(action: str, target_id: int) -> InlineKeyboardMarkup:
    """
    Generic Yes/No confirmation for destructive admin actions
    (delete/remove/end/cancel/ban). `action` is the callback_data prefix
    of the action being confirmed (e.g. "admin:giveaways:delete");
    Yes/No append ":confirm:<id>" / ":cancel:<id>" to it, so the caller
    only needs to register those two extra routes.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Yes", callback_data=f"{action}:confirm:{target_id}")
    builder.button(text="❌ No", callback_data=f"{action}:cancel:{target_id}")
    builder.adjust(2)
    return builder.as_markup()
