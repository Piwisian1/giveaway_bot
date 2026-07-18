"""
Upserts the calling user into the users table on every update, so every
downstream handler can assume the user row already exists.
"""

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from bot.db.connection import get_connection
from bot.db.repositories.user_repo import UserRepository
from bot.services.user_service import UserService


class UserTrackingMiddleware(BaseMiddleware):
    """Ensures a users row exists (and last_seen_at is fresh) for the caller."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is not None and not user.is_bot:
            service = UserService(UserRepository(get_connection()))
            await service.touch(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                language_code=user.language_code,
            )
        return await handler(event, data)
