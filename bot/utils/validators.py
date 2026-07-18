"""
Input validation for admin-composed content (giveaway title/description,
etc.) — length limits and basic content checks before anything is
persisted or reflected back into a Telegram message.
"""

MAX_TITLE_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 1000
MAX_PRIZE_LENGTH = 200


def validate_title(text: str) -> bool:
    raise NotImplementedError


def validate_description(text: str) -> bool:
    raise NotImplementedError


def validate_prize(text: str) -> bool:
    raise NotImplementedError
