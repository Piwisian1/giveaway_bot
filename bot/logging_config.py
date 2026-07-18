"""
Logging setup for the whole application.

Configures the root logger once, at startup, with:
  - a console handler (stdout) for local/systemd-journal visibility
  - a rotating file handler capturing INFO+ to logs/bot.log
  - a rotating file handler capturing ERROR+ to logs/error.log

Every other module just uses `logging.getLogger(__name__)` and inherits
this configuration — nothing else needs to touch handlers directly.
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB per file
_BACKUP_COUNT = 5


def configure_logging(log_dir: str, level: int = logging.INFO) -> None:
    """Configures the root logger. Safe to call exactly once, at process startup."""
    os.makedirs(log_dir, exist_ok=True)
    formatter = logging.Formatter(_LOG_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    bot_file_handler = RotatingFileHandler(
        os.path.join(log_dir, "bot.log"),
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    bot_file_handler.setLevel(level)
    bot_file_handler.setFormatter(formatter)

    error_file_handler = RotatingFileHandler(
        os.path.join(log_dir, "error.log"),
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(bot_file_handler)
    root_logger.addHandler(error_file_handler)

    # aiohttp/aiogram's internal client logging is noisy at INFO; keep it at WARNING.
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
