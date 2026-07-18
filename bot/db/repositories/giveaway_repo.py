"""
Data access for the giveaways table. Only one giveaway may be active at
a time — see Giveaway's docstring in bot/db/models.py.

giveaway_required_channels (a distinct, per-giveaway concept, separate
from the global required_channels table) is untouched here.
"""

from bot.db.connection import DatabaseConnection
from bot.db.models import Giveaway, GiveawayRequiredChannel

_FIELDS = (
    "id",
    "title",
    "description",
    "first_prize",
    "second_prize",
    "third_prize",
    "bonus_prize",
    "start_at",
    "end_at",
    "is_active",
)


def _row_to_giveaway(row: dict) -> Giveaway:
    return Giveaway(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        first_prize=row["first_prize"],
        second_prize=row["second_prize"],
        third_prize=row["third_prize"],
        bonus_prize=row["bonus_prize"],
        start_at=row["start_at"],
        end_at=row["end_at"],
        is_active=bool(row["is_active"]),
    )


class GiveawayRepository:
    def __init__(self, connection: DatabaseConnection) -> None:
        self._connection = connection

    async def create(self, data: dict) -> Giveaway:
        """Inserts a new, inactive giveaway. Use activate() to make it live."""
        giveaway_id = await self._connection.execute_write(
            """
            INSERT INTO giveaways
                (title, description, first_prize, second_prize, third_prize, bonus_prize, start_at, end_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (
                data["title"],
                data.get("description"),
                data.get("first_prize"),
                data.get("second_prize"),
                data.get("third_prize"),
                data.get("bonus_prize"),
                data.get("start_at"),
                data.get("end_at"),
            ),
        )
        return await self.get_by_id(giveaway_id)

    async def get_by_id(self, giveaway_id: int) -> Giveaway | None:
        row = await self._connection.fetch_one(
            "SELECT * FROM giveaways WHERE id = ?", (giveaway_id,)
        )
        return _row_to_giveaway(row) if row is not None else None

    async def get_active(self) -> Giveaway | None:
        """
        Returns the single currently-active giveaway, if any — excluding
        one whose end_at has already passed, even if the auto-closer
        (bot/background/auto_closer.py) hasn't ticked yet. Every caller
        (the /start card, the main menu, the participate flow) already
        treats None as "nothing to show/join", so this one check closes
        the entry window for every one of them at once, using the exact
        same end_at <= now() boundary the auto-closer uses to decide a
        giveaway is due.
        """
        row = await self._connection.fetch_one(
            "SELECT * FROM giveaways WHERE is_active = 1 AND (end_at IS NULL OR end_at > datetime('now'))"
        )
        return _row_to_giveaway(row) if row is not None else None

    async def list_all(self) -> list[Giveaway]:
        """Returns every giveaway, active or not, newest first — for the admin screen."""
        rows = await self._connection.fetch_all("SELECT * FROM giveaways ORDER BY id DESC")
        return [_row_to_giveaway(row) for row in rows]

    async def update_field(self, giveaway_id: int, field: str, value: str | None) -> None:
        """Updates a single column. `field` must be one of the known giveaway columns."""
        if field not in _FIELDS or field in ("id", "is_active"):
            raise ValueError(f"Cannot update field: {field}")
        await self._connection.execute_write(
            f"UPDATE giveaways SET {field} = ? WHERE id = ?",
            (value, giveaway_id),
        )

    async def delete(self, giveaway_id: int) -> None:
        """Permanently removes a giveaway."""
        await self._connection.execute_write("DELETE FROM giveaways WHERE id = ?", (giveaway_id,))

    async def activate(self, giveaway_id: int) -> None:
        """Makes the given giveaway the sole active one, deactivating any other."""
        await self._connection.execute_write(
            "UPDATE giveaways SET is_active = 0 WHERE is_active = 1"
        )
        await self._connection.execute_write(
            "UPDATE giveaways SET is_active = 1 WHERE id = ?", (giveaway_id,)
        )

    async def deactivate(self, giveaway_id: int) -> None:
        """Marks the given giveaway as no longer active, without activating any other."""
        await self._connection.execute_write(
            "UPDATE giveaways SET is_active = 0 WHERE id = ?", (giveaway_id,)
        )

    async def list_due_for_close(self) -> list[Giveaway]:
        """
        Active giveaways whose end_at has passed — candidates for the
        auto-closer (see bot/background/auto_closer.py). A giveaway with
        no end_at is never auto-closed; an admin must force-end it.
        """
        rows = await self._connection.fetch_all(
            """
            SELECT * FROM giveaways
            WHERE is_active = 1 AND end_at IS NOT NULL AND end_at <= datetime('now')
            ORDER BY id ASC
            """
        )
        return [_row_to_giveaway(row) for row in rows]

    async def close_if_active(self, giveaway_id: int) -> bool:
        """
        Atomically deactivates the giveaway iff it was still active — the
        concurrency guard that stops the same giveaway from being closed
        and drawn twice by two racing callers (e.g. the auto-closer and a
        manual admin force-end running on the same event loop). Returns
        whether this call actually closed it.
        """
        rowcount = await self._connection.execute_write_rowcount(
            "UPDATE giveaways SET is_active = 0 WHERE id = ? AND is_active = 1",
            (giveaway_id,),
        )
        return rowcount > 0

    async def get_required_channels(self, giveaway_id: int) -> list[GiveawayRequiredChannel]:
        raise NotImplementedError

    async def add_required_channel(self, giveaway_id: int, chat_id: int, chat_username: str | None) -> None:
        raise NotImplementedError
