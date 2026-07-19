"""
Inline keyboards for user-facing screens.
"""

from urllib.parse import quote

from aiogram.types import CopyTextButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.db.models import RequiredChannel

_SHARE_CAPTION = "🎁 Join this giveaway!"


def main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🚀 Join Giveaway", callback_data="menu:participate")
    builder.button(text="📜 Rules", callback_data="menu:rules")
    builder.button(text="👥 Invite", callback_data="menu:invite_friends")
    builder.adjust(1, 2)
    return builder.as_markup()


def confirmation_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="👥 Invite Friends", callback_data="menu:invite_friends")
    builder.button(text="🏠 Menu", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()


def rules_kb(show_join: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if show_join:
        builder.button(text="🚀 Join Giveaway", callback_data="menu:participate")
    builder.button(text="🔙 Back", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()


def invite_kb(link: str) -> InlineKeyboardMarkup:
    share_url = (
        f"https://t.me/share/url?"
        f"url={quote(link, safe='')}"
        f"&text={quote(_SHARE_CAPTION, safe='')}"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="📤 Share", url=share_url)
    builder.button(text="📋 Copy Link", copy_text=CopyTextButton(text=link))
    builder.button(text="🔙 Back", callback_data="menu:main")
    builder.adjust(2, 1)
    return builder.as_markup()


def menu_only_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Menu", callback_data="menu:main")
    return builder.as_markup()


def participate_kb(
    channels: list[RequiredChannel],
    retry: bool = False,
) -> InlineKeyboardMarkup:
    """
    Required Channels keyboard.
    """

    builder = InlineKeyboardBuilder()

    channel_rows = 0

    for channel in channels:
        url = (
            channel.invite_link
            or (
                f"https://t.me/{channel.username}"
                if channel.username
                else None
            )
        )

        if url:
            builder.button(
                text=f"📢 {channel.title}",
                url=url,
            )
            channel_rows += 1

    # 👇 Изменено только это
    action_text = "🔄 Check Again" if retry else "🚀 Join Giveaway"

    builder.button(
        text=action_text,
        callback_data="participate:check_subscription",
    )

    builder.button(
        text="🔙 Back",
        callback_data="menu:main",
    )

    builder.adjust(*([1] * channel_rows), 1, 1)

    return builder.as_markup()