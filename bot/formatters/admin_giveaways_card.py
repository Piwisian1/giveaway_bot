"""
Builds the text for the admin "🎁 Giveaway" management screens: the
giveaway list, the pick-a-giveaway prompts (edit/delete/activate), and
the single-giveaway edit-field view. Counterpart to
bot/formatters/giveaway_card.py, which renders the active giveaway for
regular users.
"""

from bot.db.models import Giveaway
from bot.utils.formatting import escape_html

NO_GIVEAWAYS_CONFIGURED = "⚠️ No giveaways created yet."

_EDIT_FIELD_LABELS = {
    "title": "Title",
    "description": "Description",
    "first_prize": "1st Prize",
    "second_prize": "2nd Prize",
    "third_prize": "3rd Prize",
    "bonus_prize": "Bonus Prize",
    "start_at": "Start Date",
    "end_at": "End Date",
}


def render_giveaways_screen(giveaways: list[Giveaway]) -> str:
    """
    Renders the giveaway list for the root 🎁 Giveaway screen. The
    active giveaway carries a 🟢 marker; every other one carries none —
    the same convention used unexplained in giveaways_pick_kb, so no
    legend line is needed here either.
    """
    if not giveaways:
        return f"🎁 <b>Giveaways</b>\n\n{NO_GIVEAWAYS_CONFIGURED}"

    lines = ["🎁 <b>Giveaways</b>", ""]
    for giveaway in giveaways:
        marker = "🟢 " if giveaway.is_active else ""
        lines.append(f"{marker}{escape_html(giveaway.title)}")
    return "\n".join(lines)


def render_pick_giveaway_prompt(action_title: str, giveaways: list[Giveaway]) -> str:
    """Renders the prompt shown above the per-giveaway picker buttons."""
    if not giveaways:
        return NO_GIVEAWAYS_CONFIGURED
    return f"{action_title}\n\nTap a giveaway:"


def render_giveaway_edit_screen(giveaway: Giveaway) -> str:
    """Renders the current field values for the edit-a-single-field screen."""
    lines = [f"✏️ <b>Editing:</b> {escape_html(giveaway.title)}", ""]
    for field, label in _EDIT_FIELD_LABELS.items():
        value = getattr(giveaway, field)
        lines.append(f"<b>{label}:</b> {escape_html(value) if value else '<i>(not set)</i>'}")
    return "\n".join(lines)


def render_delete_confirm_prompt(giveaway: Giveaway) -> str:
    """Renders the Yes/No confirmation shown before permanently deleting a giveaway."""
    return f"🗑 <b>Delete {escape_html(giveaway.title)}?</b>\n\nThis can't be undone."


def field_label(field: str) -> str:
    return _EDIT_FIELD_LABELS[field]
