"""
Small formatting helpers shared across formatters/handlers.
"""

import html
from datetime import datetime


def escape_html(text: str) -> str:
    """Escapes user-provided text before it's interpolated into an HTML-parse-mode message."""
    return html.escape(text)


def format_display_date(value: str) -> str:
    """
    Formats a stored 'YYYY-MM-DD HH:MM:SS' timestamp (see
    bot/handlers/admin/giveaways.py) as e.g. 'Aug 1, 8:00 PM'.

    Built from strftime's portable directives only (no %-d/%#d, which
    differ between Linux and Windows) so it behaves the same on every
    deployment target.
    """
    parsed = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    hour_12 = parsed.hour % 12 or 12
    period = "AM" if parsed.hour < 12 else "PM"
    return f"{parsed.strftime('%b')} {parsed.day}, {hour_12}:{parsed.minute:02d} {period}"


def format_time_remaining(ends_at: str) -> str:
    """Formats a countdown string (e.g. '2d 4h 12m') from an ISO timestamp."""
    raise NotImplementedError


def pluralize(count: int, singular: str, plural: str) -> str:
    """Returns the singular or plural form of a word based on count."""
    return singular if count == 1 else plural
