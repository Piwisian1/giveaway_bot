"""
Builds the text for the admin "Required Channels" management screen and
its Remove-channel picker. Counterpart to bot/formatters/participate_card.py,
which renders the same data for regular users.
"""

from bot.db.models import RequiredChannel
from bot.utils.formatting import escape_html

NO_CHANNELS_CONFIGURED = "⚠️ No required channels configured yet."


def render_admin_channels_screen(channels: list[RequiredChannel]) -> str:
    """Renders the list of active required channels for the admin screen."""
    if not channels:
        return f"📢 <b>Required Channels</b>\n\n{NO_CHANNELS_CONFIGURED}"

    lines = ["📢 <b>Required Channels</b>", ""]
    lines.extend(
        f"{index}. 📌 {escape_html(channel.title)}" for index, channel in enumerate(channels, start=1)
    )
    return "\n".join(lines)


def render_remove_channel_prompt(channels: list[RequiredChannel]) -> str:
    """Renders the prompt shown above the per-channel delete buttons."""
    if not channels:
        return NO_CHANNELS_CONFIGURED
    return "🗑 <b>Remove Channel</b>\n\nTap a channel below to remove it:"


def render_remove_channel_confirm_prompt(channel: RequiredChannel) -> str:
    """Renders the Yes/No confirmation shown before permanently removing a required channel."""
    return (
        f"🗑 <b>Remove {escape_html(channel.title)}?</b>\n\n"
        "Users will no longer need to join it to enter."
    )
