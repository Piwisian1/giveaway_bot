"""
Simple in-memory per-user rate limiting (no Redis needed at this scale
— single process, one dict of last-call timestamps keyed by
telegram_id).
"""

import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject


class ThrottlingMiddleware(BaseMiddleware):
    """Drops updates from a user calling handlers too frequently."""

    def __init__(self, rate_limit_seconds: float = 0.5) -> None:
        self._rate_limit_seconds = rate_limit_seconds
        self._last_call: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is not None:
            now = time.monotonic()
            last_call = self._last_call.get(user.id)
            if last_call is not None and now - last_call < self._rate_limit_seconds:
                if isinstance(event, CallbackQuery):
                    # Close the tap's loading spinner without a visible toast.
                    await event.answer()
                return None
            self._last_call[user.id] = now
        return await handler(event, data)
