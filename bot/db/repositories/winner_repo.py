"""
Data access for the winners table.
"""

from bot.db.connection import DatabaseConnection
from bot.db.models import Winner


def _row_to_winner(row: dict) -> Winner:
    return Winner(
        id=row["id"],
        giveaway_id=row["giveaway_id"],
        user_id=row["user_id"],
        position=row["position"],
        drawn_at=row["drawn_at"],
        notified=bool(row["notified"]),
    )


class WinnerRepository:
    def __init__(self, connection: DatabaseConnection) -> None:
        self._connection = connection

    async def create(self, giveaway_id: int, user_id: int, position: int) -> Winner:
        winner_id = await self._connection.execute_write(
            "INSERT INTO winners (giveaway_id, user_id, position) VALUES (?, ?, ?)",
            (giveaway_id, user_id, position),
        )
        row = await self._connection.fetch_one("SELECT * FROM winners WHERE id = ?", (winner_id,))
        assert row is not None
        return _row_to_winner(row)

    async def list_for_giveaway(self, giveaway_id: int) -> list[Winner]:
        rows = await self._connection.fetch_all(
            "SELECT * FROM winners WHERE giveaway_id = ? ORDER BY position ASC",
            (giveaway_id,),
        )
        return [_row_to_winner(row) for row in rows]

    async def mark_notified(self, winner_id: int) -> None:
        await self._connection.execute_write(
            "UPDATE winners SET notified = 1 WHERE id = ?", (winner_id,)
        )

    async def delete_for_giveaway(self, giveaway_id: int) -> None:
        """Used by reroll to clear previous winners before drawing again."""
        await self._connection.execute_write(
            "DELETE FROM winners WHERE giveaway_id = ?", (giveaway_id,)
        )
