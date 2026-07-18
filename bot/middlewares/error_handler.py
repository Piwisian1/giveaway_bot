"""
Global error boundary: logs full tracebacks to logs/error.log and
ensures the end user only ever sees a generic, safe error message.
"""

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.texts.en import GENERIC_ERROR

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseMiddleware):
    """Wraps handler execution, catching and logging unhandled exceptions."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception:
            logger.exception("Unhandled error while processing update")
            try:
                if isinstance(event, CallbackQuery):
                    await event.answer(GENERIC_ERROR, show_alert=True)
                elif isinstance(event, Message):
                    await event.answer(GENERIC_ERROR)
            except Exception:
                logger.exception("Failed to notify the user after an unhandled error")
            return None
