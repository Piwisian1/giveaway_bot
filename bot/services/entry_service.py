"""
Business logic for joining a giveaway: idempotent entry creation, and
per-user entry status lookups — this is what drives whether a giveaway
detail view shows "🎉 Participate" or "✅ You're Participating".
"""

from bot.db.repositories.entry_repo import EntryRepository


class EntryService:
    """Coordinates giveaway entries on top of EntryRepository."""

    def __init__(self, repo: EntryRepository) -> None:
        self._repo = repo

    async def has_entered(self, giveaway_id: int, user_id: int) -> bool:
        """Returns whether the given user already has an entry for this giveaway."""
        return await self._repo.get(giveaway_id, user_id) is not None

    async def join(self, giveaway_id: int, user_id: int) -> bool:
        """
        Creates the entry (base ticket) if one doesn't already exist and
        the giveaway is still open — atomically, so it can't succeed
        against a giveaway that closed moments ago (see
        EntryRepository.create). Safe to call multiple times — enforced
        by the UNIQUE constraint on (giveaway_id, user_id).

        Returns whether the user is now entered. False means the
        giveaway closed just before this call and no entry was created;
        the caller must not treat that as a successful join.
        """
        entry = await self._repo.create(giveaway_id, user_id)
        return entry is not None

    async def count_participants(self, giveaway_id: int) -> int:
        """
        Returns the current participant count for a giveaway. Called
        right after join() so the number doubles as the joining user's
        ticket number — see bot/handlers/user/participate.py.
        """
        return await self._repo.count_for_giveaway(giveaway_id)

    async def list_entries_for_user(self, user_id: int) -> list:
        """Returns all of a user's entries, for the 'My Tickets' screen."""
        raise NotImplementedError
