"""
Data access for the admin_logs audit table.
"""

from bot.db.connection import DatabaseConnection
from bot.db.models import AdminLog


class AdminLogRepository:
    def __init__(self, connection: DatabaseConnection) -> None:
        self._connection = connection

    async def log(self, admin_id: int, action: str, target: str | None = None, details: str | None = None) -> None:
        raise NotImplementedError

    async def list_recent(self, limit: int = 50) -> list[AdminLog]:
        raise NotImplementedError
