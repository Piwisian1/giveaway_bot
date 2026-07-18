"""
Inline keyboards for user-facing screens.
"""

from urllib.parse import quote

from aiogram.types import CopyTextButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.db.models import RequiredChannel

# Caption shown alongside the link in Telegram's native share sheet —
# see invite_kb(). Separate from the in-bot screen copy in
# bot/formatters/referral_card.py.
_SHARE_CAPTION = "🎁 Join this giveaway!"


def main_menu_kb() -> InlineKeyboardMarkup:
    """
    Main Giveaway Card keyboard, per the UX specification: 🚀 Join
    Giveaway alone as the primary action, with 📜 Rules and 👥 Invite
    sharing one secondary row.

    Join Giveaway is wired up (see bot/handlers/user/participate.py),
    Rules in bot/handlers/user/menu.py, Invite in
    bot/handlers/user/referral.py.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="🚀 Join Giveaway", callback_data="menu:participate")
    builder.button(text="📜 Rules", callback_data="menu:rules")
    builder.button(text="👥 Invite", callback_data="menu:invite_friends")
    builder.adjust(1, 2)
    return builder.as_markup()


def confirmation_kb() -> InlineKeyboardMarkup:
    """
    Keyboard shown after Registration Success and on Already
    Participating, per the UX specification: 👥 Invite Friends as the
    primary action, 🏠 Menu as the only secondary.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="👥 Invite Friends", callback_data="menu:invite_friends")
    builder.button(text="🏠 Menu", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()


def rules_kb(show_join: bool) -> InlineKeyboardMarkup:
    """
    Rules screen keyboard: 🚀 Join Giveaway appears only for a visitor
    who hasn't entered yet; a returning, already-entered visitor sees
    Back alone, per the UX specification.
    """
    builder = InlineKeyboardBuilder()
    if show_join:
        builder.button(text="🚀 Join Giveaway", callback_data="menu:participate")
    builder.button(text="🔙 Back", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()


def invite_kb(link: str) -> InlineKeyboardMarkup:
    """
    Invite Friends keyboard: 📤 Share is the primary action, using
    Telegram's native "share to chat" deep link (t.me/share/url) —
    this needs no inline-mode setup, unlike switch_inline_query. 📋 Copy
    Link is the secondary action sharing the same row (Telegram's
    native copy-to-clipboard button, Bot API 7+). 🔙 Back sits alone on
    its own row, per the pattern used everywhere else.
    """
    share_url = f"https://t.me/share/url?url={quote(link, safe='')}&text={quote(_SHARE_CAPTION, safe='')}"
    builder = InlineKeyboardBuilder()
    builder.button(text="📤 Share", url=share_url)
    builder.button(text="📋 Copy Link", copy_text=CopyTextButton(text=link))
    builder.button(text="🔙 Back", callback_data="menu:main")
    builder.adjust(2, 1)
    return builder.as_markup()


def menu_only_kb() -> InlineKeyboardMarkup:
    """A single 🏠 Menu button — used by screens with nothing else to act on yet."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Menu", callback_data="menu:main")
    return builder.as_markup()


def participate_kb(channels: list[RequiredChannel], retry: bool = False) -> InlineKeyboardMarkup:
    """
    Required Channels / Almost There keyboard: one URL button per
    channel (built dynamically — no hardcoded channels, one per row so
    a long channel name never truncates), then the action button alone
    on its own row (same primary-action-isolated pattern as
    main_menu_kb) with 'Back' on a trailing row beneath it.

    The action button reads 'Participate' on the first pass and
    'Check Again' once the visitor has already tried and come up
    short (retry=True) — both wire to the same callback, which
    triggers live membership verification, see
    bot/handlers/user/participate.py. 'Back' returns to the main menu.
    """
    builder = InlineKeyboardBuilder()
    channel_rows = 0
    for channel in channels:
        url = channel.invite_link or (f"https://t.me/{channel.username}" if channel.username else None)
        if url:
            builder.button(text=f"📢 {channel.title}", url=url)
            channel_rows += 1
    action_text = "🔁 Check Again" if retry else "✅ Participate"
    builder.button(text=action_text, callback_data="participate:check_subscription")
    builder.button(text="🔙 Back", callback_data="menu:main")
    builder.adjust(*([1] * channel_rows), 1, 1)
    return builder.as_markup()
