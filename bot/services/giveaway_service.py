"""
Business logic for giveaway management. Only one giveaway can be active
at a time — see Giveaway's docstring in bot/db/models.py. Does not
implement participant registration or winner selection (see
bot/services/entry_service.py / bot/services/winner_service.py).
"""

from bot.db.models import Giveaway
from bot.db.repositories.giveaway_repo import GiveawayRepository


def derive_status(giveaway: Giveaway, has_winners: bool) -> str:
    """
    Derives a display status from is_active + whether winners have been
    drawn — there's no separate status column (see Giveaway in
    bot/db/models.py). "inactive" covers both a never-activated draft
    and a giveaway cancelled before any draw; those two are otherwise
    indistinguishable from what the schema stores today.
    """
    if giveaway.is_active:
        return "active"
    if has_winners:
        return "ended"
    return "inactive"


class GiveawayService:
    """Coordinates giveaway CRUD + activation on top of GiveawayRepository."""

    def __init__(self, repo: GiveawayRepository) -> None:
        self._repo = repo

    async def create(self, data: dict) -> Giveaway:
        """Creates a new giveaway, inactive by default."""
        return await self._repo.create(data)

    async def get_by_id(self, giveaway_id: int) -> Giveaway | None:
        return await self._repo.get_by_id(giveaway_id)

    async def get_active(self) -> Giveaway | None:
        """Returns the currently active giveaway, or None if none is active."""
        return await self._repo.get_active()

    async def list_all(self) -> list[Giveaway]:
        """Returns every giveaway, for the admin management screen."""
        return await self._repo.list_all()

    async def update_field(self, giveaway_id: int, field: str, value: str | None) -> None:
        """Updates a single editable field on an existing giveaway."""
        await self._repo.update_field(giveaway_id, field, value)

    async def delete(self, giveaway_id: int) -> None:
        """Permanently removes a giveaway."""
        await self._repo.delete(giveaway_id)

    async def activate(self, giveaway_id: int) -> None:
        """Activates the given giveaway, deactivating whichever one was active before."""
        await self._repo.activate(giveaway_id)

    async def deactivate(self, giveaway_id: int) -> None:
        """Deactivates the given giveaway without activating another — used to cancel it."""
        await self._repo.deactivate(giveaway_id)
