"""
Builds the Main Giveaway Card — the /start and 'Back to menu' screen.

Rendered as stacked blocks — title, first prize, end date, required-
channels teaser, description — joined with a blank line each so the
card reads cleanly no matter which fields are filled in. No dividers,
no participant count, no per-tier prize breakdown. Second/third/bonus
prizes still live on the giveaway record for the admin screens; this
card deliberately shows only what a visitor needs to decide whether to
enter.

The required-channels line here is a teaser only (channel count, not
the channels themselves) — the actual per-channel buttons and live
membership verification happen one tap later, on the Required Channels
screen (see bot/formatters/participate_card.py and
bot/handlers/user/participate.py). That flow is unchanged; this file
only decides what's visible before the visitor commits to joining.

The block helpers below are private on purpose: render_giveaway_card
(the channel-announcement variant, currently unimplemented — see its
docstring) is meant to reuse them once its extra fields exist, rather
than re-deriving this layout from scratch.
"""

from bot.db.models import Giveaway
from bot.utils.formatting import escape_html, format_display_date, pluralize

NO_ACTIVE_GIVEAWAY = "🎁 <b>No Active Giveaway</b>\n\n<i>Check back soon — the next one is on its way.</i>"

_DEFAULT_TAGLINE = "One winner, drawn live in this chat."
_NO_PRIZE_YET = "Prize to be announced"


def _title_block(title: str) -> str:
    return f"🎁 <b>{escape_html(title)}</b>"


def _first_prize_block(first_prize: str | None) -> str:
    prize = escape_html(first_prize) if first_prize else _NO_PRIZE_YET
    return f"🏆 <b>First Prize</b>\n{prize}"


def _end_date_block(end_at: str | None) -> str:
    ends = format_display_date(end_at) if end_at else "soon"
    return f"⏳ <b>Ends:</b> {ends}"


def _required_channels_block(channel_count: int) -> str | None:
    """
    Teaser line only — omitted entirely when no channels are required,
    so a giveaway with a free entry never shows an empty/misleading
    gate. Full per-channel buttons live on the next screen.
    """
    if channel_count <= 0:
        return None
    noun = pluralize(channel_count, "channel", "channels")
    return f"🔒 <b>Required Channels</b>\nJoin {channel_count} {noun} to unlock your entry."


def _description_block(description: str | None) -> str:
    tagline = escape_html(description) if description else _DEFAULT_TAGLINE
    return f"<i>{tagline}</i>"


def render_active_giveaway(giveaway: Giveaway | None, required_channel_count: int = 0) -> str:
    """
    Renders the currently active giveaway, or the no-active-giveaway
    fallback. `required_channel_count` is the number of currently
    active required channels (0 if none configured) — see
    RequiredChannelService.get_active_channels, called by the /start
    and main-menu handlers before this.
    """
    if giveaway is None:
        return NO_ACTIVE_GIVEAWAY

    blocks = [
        _title_block(giveaway.title),
        _first_prize_block(giveaway.first_prize),
        _end_date_block(giveaway.end_at),
        _required_channels_block(required_channel_count),
        _description_block(giveaway.description),
    ]
    return "\n\n".join(block for block in blocks if block is not None)


def render_giveaway_card(giveaway: Giveaway, participant_count: int, time_remaining: str) -> str:
    """
    Renders the public announcement card for a channel/group post: the
    same minimal shape as render_active_giveaway (headline prize, one
    line of context, blank line, timing) plus a participant count line —
    no dividers, per the UX specification.

    Called by:
      - bot/handlers/user/giveaways.py (initial render on view/join)
      - bot/background/live_updater.py (periodic refresh of the same
        message — participant_count and time_remaining change, layout
        stays identical)
    """
    raise NotImplementedError


def render_winners_announcement(giveaway: Giveaway, winners: list) -> str:
    """
    Renders the "giveaway ended, here are the winners" card, used to
    edit the original announcement message in place once the auto-
    closer / winner_service completes a draw.
    """
    raise NotImplementedError
