"""
Builds the text for every screen in the join flow after the Main
Giveaway Card: Required Channels, Almost There (the missing-channel
retry), Already Participating, and Registration Success. Copy and
structure are taken verbatim from the UX specification — see
bot/keyboards/user_kb.py for the matching button layouts
(participate_kb, confirmation_kb).
"""

from bot.db.models import RequiredChannel
from bot.utils.formatting import escape_html, format_display_date, pluralize

NO_CHANNELS_CONFIGURED = "⚠️ No required channels have been configured yet."
NO_ACTIVE_GIVEAWAY_VERIFIED = "✅ <b>You're verified!</b>\n\nThere is no active giveaway to enter right now — check back soon."


def render_participate_screen(channels: list[RequiredChannel]) -> str:
    """
    Renders the Required Channels screen, shown above the Participate
    button. Channel names appear only as buttons (see participate_kb)
    — the spec deliberately doesn't repeat them in the message text.
    """
    if not channels:
        return NO_CHANNELS_CONFIGURED
    noun = pluralize(len(channels), "channel", "channels")
    return (
        f"🔐 <b>Last Step</b>\n\n"
        f"Join the required {noun} below, then tap <b>Participate</b> to confirm your entry."
    )


def render_missing_channels(missing: list[RequiredChannel]) -> str:
    """
    Renders the Almost There screen, scoped to only the channels still
    outstanding — a returning visitor never has to re-read channels
    they've already joined.
    """
    lines = ["🔓 <b>Almost There</b>", "", "You're just missing:"]
    lines.extend(f"📢 {escape_html(channel.title)}" for channel in missing)
    lines.append("")
    lines.append(f"Join {pluralize(len(missing), 'it', 'them')}, then tap <b>Check Again</b>.")
    return "\n".join(lines)


def render_already_participating(end_at: str | None) -> str:
    """Renders the Already Participating screen for a returning, already-entered visitor."""
    when = f"on {format_display_date(end_at)}" if end_at else "soon"
    return f"✅ <b>You're already entered!</b>\n\n⏳ Sit tight — the draw happens {when}, live in this chat."


def render_verified(entered: bool, ticket_number: int | None = None, end_at: str | None = None) -> str:
    """
    Renders the Registration Success screen, or the no-active-giveaway
    fallback if the giveaway was deactivated between the channel check
    and this confirmation.
    """
    if not entered:
        return NO_ACTIVE_GIVEAWAY_VERIFIED

    when = f"on {format_display_date(end_at)}" if end_at else "soon"
    have_entered = pluralize(ticket_number, "person has", "people have")
    return (
        f"✅ <b>You're in!</b>\n\n"
        f"🎟 <b>Ticket #{ticket_number}</b> · {ticket_number} {have_entered} entered\n\n"
        f"🍀 Good luck — the winner is drawn live in this chat {when}."
    )
