"""
Builds the text for the admin giveaway lifecycle screens: the
manage-list, the single-giveaway management view (with its winners once
ended), and the End/Cancel/Reroll confirmation prompts. Counterpart to
bot/formatters/admin_giveaways_card.py, which handles the CRUD screens
(create/edit/delete/activate) for the same giveaways.
"""

from bot.db.models import Giveaway, User, Winner
from bot.formatters.admin_giveaways_card import NO_GIVEAWAYS_CONFIGURED
from bot.services.giveaway_service import derive_status
from bot.utils.formatting import escape_html

_STATUS_MARKERS = {"active": "🟢", "ended": "🏁", "inactive": "⚪"}
_POSITION_MARKERS = {1: "🥇", 2: "🥈", 3: "🥉"}


def _display_name(user: User) -> str:
    if user.first_name:
        return escape_html(user.first_name)
    if user.username:
        return f"@{escape_html(user.username)}"
    return f"ID {user.telegram_id}"


def _position_marker(position: int) -> str:
    return _POSITION_MARKERS.get(position, f"#{position}")


def render_manage_list_screen(giveaways: list[Giveaway], has_winners: dict[int, bool]) -> str:
    """Renders every giveaway with a status marker, for the manage-list picker."""
    if not giveaways:
        return f"📋 <b>Manage Giveaways</b>\n\n{NO_GIVEAWAYS_CONFIGURED}"

    lines = ["📋 <b>Manage Giveaways</b>", ""]
    for giveaway in giveaways:
        status = derive_status(giveaway, has_winners.get(giveaway.id, False))
        marker = _STATUS_MARKERS[status]
        lines.append(f"{marker} {escape_html(giveaway.title)}")
    return "\n".join(lines)


def render_giveaway_manage_screen(
    giveaway: Giveaway,
    winners: list[Winner],
    winner_users: dict[int, User],
    participant_count: int,
) -> str:
    """
    Renders a single giveaway's management screen: status, entrant
    count, and — once ended — the drawn winners in position order.
    """
    status = derive_status(giveaway, bool(winners))
    lines = [
        f"{_STATUS_MARKERS[status]} <b>{escape_html(giveaway.title)}</b>",
        "",
        f"📊 Status: <b>{status}</b>",
        f"👥 Entrants: <b>{participant_count}</b>",
    ]
    if winners:
        lines.append("")
        lines.append("🏆 <b>Winners</b>")
        for winner in winners:
            user = winner_users.get(winner.user_id)
            name = _display_name(user) if user is not None else f"user #{winner.user_id}"
            notified = "✅" if winner.notified else "⏳"
            lines.append(f"{_position_marker(winner.position)} {name} {notified}")
    return "\n".join(lines)


def render_entrants_screen(giveaway: Giveaway, participant_count: int) -> str:
    """Renders the entrant-count summary for a single giveaway."""
    return f"👥 <b>{escape_html(giveaway.title)}</b>\n\nEntrants: <b>{participant_count}</b>"


def render_end_confirm_prompt(giveaway: Giveaway) -> str:
    return (
        f"🔴 <b>End {escape_html(giveaway.title)} now?</b>\n\n"
        "This draws winners immediately from current entrants and can't be undone "
        "(though winners can be rerolled afterward)."
    )


def render_cancel_confirm_prompt(giveaway: Giveaway) -> str:
    return (
        f"🚫 <b>Cancel {escape_html(giveaway.title)}?</b>\n\n"
        "No winners will be drawn. This can't be undone."
    )


def render_reroll_confirm_prompt(giveaway: Giveaway) -> str:
    return (
        f"🔁 <b>Reroll winners for {escape_html(giveaway.title)}?</b>\n\n"
        "Previous winners are excluded from the new draw."
    )
