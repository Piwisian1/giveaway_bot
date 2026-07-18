"""
Application configuration loaded from environment variables (.env).

Centralizes all runtime settings so no other module reads os.environ
directly. Import the module-level `settings` singleton everywhere else.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _parse_admin_ids(raw: str) -> list[int]:
    """Parses a comma-separated ADMIN_IDS env value into a list of ints."""
    return [int(chunk) for chunk in raw.split(",") if chunk.strip()]


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    admin_ids: list[int]
    db_path: str
    log_dir: str
    # How often (seconds) active giveaway announcement messages are
    # refreshed (participant count + remaining time). See
    # bot/background/live_updater.py.
    live_update_interval: int
    # How often (seconds) the auto-closer checks for giveaways that
    # have passed their end time. See bot/background/auto_closer.py.
    auto_close_interval: int


def load_settings() -> Settings:
    """
    Builds a Settings instance from the current environment. Fails loudly
    and clearly on a missing BOT_TOKEN (the bot literally cannot run
    without one) rather than a bare KeyError traceback — this runs before
    configure_logging(), so both the exception and the ADMIN_IDS warning
    below are still visible via Python's default stderr handling (or
    `journalctl` under systemd) even though our own log files aren't
    wired up yet.
    """
    bot_token = os.environ.get("BOT_TOKEN")
    if not bot_token:
        raise RuntimeError(
            "BOT_TOKEN is not set. Copy .env.example to .env and fill in a "
            "real bot token from @BotFather before starting the bot."
        )

    admin_ids = _parse_admin_ids(os.environ.get("ADMIN_IDS", ""))
    if not admin_ids:
        logger.warning(
            "ADMIN_IDS is empty — no Telegram user will be able to access "
            "the admin panel (/admin). Set it in .env to your Telegram "
            "user id(s), comma-separated."
        )

    return Settings(
        bot_token=bot_token,
        admin_ids=admin_ids,
        db_path=os.environ.get("DB_PATH", "data/bot.db"),
        log_dir=os.environ.get("LOG_DIR", "logs"),
        live_update_interval=int(os.environ.get("LIVE_UPDATE_INTERVAL", "20")),
        auto_close_interval=int(os.environ.get("AUTO_CLOSE_INTERVAL", "30")),
    )


settings = load_settings()
