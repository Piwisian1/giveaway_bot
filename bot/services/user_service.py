"""
Business logic for user accounts: registration/touch, ban/unban,
profile summaries.
"""

from bot.db.models import User
from bot.db.repositories.user_repo import UserRepository


class UserService:
    """Coordinates user-related operations on top of UserRepository."""

    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def touch(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        language_code: str | None,
    ) -> User:
        """Creates the user row if missing, otherwise refreshes last_seen_at. Returns the resulting row."""
        return await self._repo.upsert(telegram_id, username, first_name, language_code)

    async def ban(self, user_id: int, admin_id: int, reason: str) -> None:
        """Bans a user and records the action to admin_logs."""
        raise NotImplementedError

    async def unban(self, user_id: int, admin_id: int) -> None:
        """Unbans a user and records the action to admin_logs."""
        raise NotImplementedError

    async def get_profile_summary(self, user_id: int) -> dict:
        """Returns join date, total entries, and total referrals for a user."""
        raise NotImplementedError
