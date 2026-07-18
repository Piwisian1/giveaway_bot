"""
Data access for the entries table.
"""

from bot.db.connection import DatabaseConnection
from bot.db.models import Entry


def _row_to_entry(row: dict) -> Entry:
    return Entry(
        id=row["id"],
        giveaway_id=row["giveaway_id"],
        user_id=row["user_id"],
        tickets=row["tickets"],
        entered_at=row["entered_at"],
    )


class EntryRepository:
    def __init__(self, connection: DatabaseConnection) -> None:
        self._connection = connection

    async def get(self, giveaway_id: int, user_id: int) -> Entry | None:
        row = await self._connection.fetch_one(
            "SELECT * FROM entries WHERE giveaway_id = ? AND user_id = ?",
            (giveaway_id, user_id),
        )
        return _row_to_entry(row) if row is not None else None

    async def create(self, giveaway_id: int, user_id: int, tickets: int = 1) -> Entry | None:
        """
        Idempotent via UNIQUE(giveaway_id, user_id) — a repeat call for an
        existing entry is a no-op and still returns that entry.

        The insert itself only fires if the giveaway is still open
        (active, end_at not passed) at the moment this statement runs —
        checked and inserted in one atomic write through the single-
        writer queue, not as a separate check beforehand, so a giveaway
        closing in the gap between the caller's own checks (e.g. reading
        get_active()) and this call can't let someone sneak in. Returns
        None if the giveaway was already closed and no prior entry
        exists — the caller (see EntryService.join) must treat that as
        "did not join", not silently succeed.
        """
        await self._connection.execute_write(
            """
            INSERT INTO entries (giveaway_id, user_id, tickets)
            SELECT ?, ?, ?
            WHERE EXISTS (
                SELECT 1 FROM giveaways
                WHERE id = ? AND is_active = 1 AND (end_at IS NULL OR end_at > datetime('now'))
            )
            ON CONFLICT(giveaway_id, user_id) DO NOTHING
            """,
            (giveaway_id, user_id, tickets, giveaway_id),
        )
        return await self.get(giveaway_id, user_id)

    async def add_tickets(self, giveaway_id: int, user_id: int, amount: int) -> None:
        """Adds (or, with a negative amount, removes) tickets on an existing entry. No-ops if none exists."""
        await self._connection.execute_write(
            "UPDATE entries SET tickets = tickets + ? WHERE giveaway_id = ? AND user_id = ?",
            (amount, giveaway_id, user_id),
        )

    async def count_for_giveaway(self, giveaway_id: int) -> int:
        row = await self._connection.fetch_one(
            "SELECT COUNT(*) AS count FROM entries WHERE giveaway_id = ?",
            (giveaway_id,),
        )
        return row["count"]

    async def list_for_giveaway(self, giveaway_id: int) -> list[Entry]:
        rows = await self._connection.fetch_all(
            "SELECT * FROM entries WHERE giveaway_id = ?", (giveaway_id,)
        )
        return [_row_to_entry(row) for row in rows]

    async def list_for_user(self, user_id: int) -> list[Entry]:
        raise NotImplementedError
