"""
Blocks admin-router updates from non-admins before they reach any admin
handler. This is the sole authorization gate for the entire Telegram-
native admin panel (see bot/handlers/admin/), applied to those routers
in bot/loader.py.
"""

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject

from bot.config import settings


class AdminGuardMiddleware(BaseMiddleware):
    """Rejects updates whose sender is not in settings.admin_ids."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None or user.id not in settings.admin_ids:
            if isinstance(event, CallbackQuery):
                await event.answer("You're not authorized to do that.", show_alert=True)
            return None
        return await handler(event, data)
