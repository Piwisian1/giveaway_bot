"""
Data access for the required_channels table — the global list of
channels a user must join to participate. This is deliberately
separate from GiveawayRepository's per-giveaway required-channels
concept (giveaway_required_channels), which is untouched here.
"""

from bot.db.connection import DatabaseConnection
from bot.db.models import RequiredChannel


def _row_to_channel(row: dict) -> RequiredChannel:
    return RequiredChannel(
        id=row["id"],
        telegram_chat_id=row["telegram_chat_id"],
        username=row["username"],
        title=row["title"],
        invite_link=row["invite_link"],
        sort_order=row["sort_order"],
        is_active=bool(row["is_active"]),
    )


class RequiredChannelRepository:
    def __init__(self, connection: DatabaseConnection) -> None:
        self._connection = connection

    async def list_active(self) -> list[RequiredChannel]:
        """Returns active required channels, ordered for display on the Participate screen."""
        rows = await self._connection.fetch_all(
            """
            SELECT id, telegram_chat_id, username, title, invite_link, sort_order, is_active
            FROM required_channels
            WHERE is_active = 1
            ORDER BY sort_order ASC, id ASC
            """
        )
        return [_row_to_channel(row) for row in rows]

    async def list_all(self) -> list[RequiredChannel]:
        """Returns every configured channel, active or not — for the admin screen."""
        rows = await self._connection.fetch_all(
            """
            SELECT id, telegram_chat_id, username, title, invite_link, sort_order, is_active
            FROM required_channels
            ORDER BY sort_order ASC, id ASC
            """
        )
        return [_row_to_channel(row) for row in rows]

    async def get_by_id(self, channel_id: int) -> RequiredChannel | None:
        row = await self._connection.fetch_one(
            """
            SELECT id, telegram_chat_id, username, title, invite_link, sort_order, is_active
            FROM required_channels
            WHERE id = ?
            """,
            (channel_id,),
        )
        return _row_to_channel(row) if row is not None else None

    async def create(
        self,
        telegram_chat_id: int,
        title: str,
        username: str | None = None,
        invite_link: str | None = None,
        sort_order: int = 0,
    ) -> RequiredChannel:
        """Adds a new required channel, active immediately."""
        channel_id = await self._connection.execute_write(
            """
            INSERT INTO required_channels
                (telegram_chat_id, username, title, invite_link, sort_order, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (telegram_chat_id, username, title, invite_link, sort_order),
        )
        return RequiredChannel(
            id=channel_id,
            telegram_chat_id=telegram_chat_id,
            username=username,
            title=title,
            invite_link=invite_link,
            sort_order=sort_order,
            is_active=True,
        )

    async def set_active(self, channel_id: int, is_active: bool) -> None:
        """Activates/deactivates a channel without deleting it — for the future admin screen."""
        raise NotImplementedError

    async def delete(self, channel_id: int) -> None:
        """Permanently removes a required channel."""
        await self._connection.execute_write(
            "DELETE FROM required_channels WHERE id = ?",
            (channel_id,),
        )
