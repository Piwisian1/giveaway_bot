"""
Data access for the users table. Only parametrized SQL — no string
formatting of untrusted input, ever.
"""

from bot.db.connection import DatabaseConnection
from bot.db.models import User


def _row_to_user(row: dict) -> User:
    return User(
        id=row["id"],
        telegram_id=row["telegram_id"],
        username=row["username"],
        first_name=row["first_name"],
        language_code=row["language_code"],
        referral_code=row["referral_code"],
        referred_by_user_id=row["referred_by_user_id"],
        pending_referrer_id=row["pending_referrer_id"],
        is_banned=bool(row["is_banned"]),
        is_admin=bool(row["is_admin"]),
        joined_at=row["joined_at"],
        last_seen_at=row["last_seen_at"],
    )


class UserRepository:
    def __init__(self, connection: DatabaseConnection) -> None:
        self._connection = connection

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        row = await self._connection.fetch_one(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        return _row_to_user(row) if row is not None else None

    async def get_by_id(self, user_id: int) -> User | None:
        row = await self._connection.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
        return _row_to_user(row) if row is not None else None

    async def get_by_referral_code(self, referral_code: str) -> User | None:
        row = await self._connection.fetch_one(
            "SELECT * FROM users WHERE referral_code = ?", (referral_code,)
        )
        return _row_to_user(row) if row is not None else None

    async def upsert(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        language_code: str | None,
    ) -> User:
        """Creates the user row if missing, otherwise refreshes their profile fields and last_seen_at."""
        await self._connection.execute_write(
            """
            INSERT INTO users (telegram_id, username, first_name, language_code)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                language_code = excluded.language_code,
                last_seen_at = datetime('now')
            """,
            (telegram_id, username, first_name, language_code),
        )
        user = await self.get_by_telegram_id(telegram_id)
        assert user is not None
        return user

    async def set_banned(self, user_id: int, is_banned: bool) -> None:
        raise NotImplementedError

    async def set_referral_code(self, user_id: int, referral_code: str) -> None:
        await self._connection.execute_write(
            "UPDATE users SET referral_code = ? WHERE id = ?",
            (referral_code, user_id),
        )

    async def set_pending_referrer(self, user_id: int, referrer_id: int) -> None:
        """
        First-touch attribution: only takes effect if this user has no
        pending referrer yet and hasn't already been credited to
        someone. A second referral link clicked later can't hijack an
        earlier one.
        """
        await self._connection.execute_write(
            """
            UPDATE users
            SET pending_referrer_id = ?
            WHERE id = ? AND pending_referrer_id IS NULL AND referred_by_user_id IS NULL
            """,
            (referrer_id, user_id),
        )

    async def finalize_referral(self, user_id: int, referrer_id: int) -> None:
        """
        Promotes a pending referrer to the permanent, immutable
        referred_by_user_id — called once, at the referred user's first
        qualifying conversion. Idempotent: a repeated call is a no-op
        since referred_by_user_id is already set after the first.
        """
        await self._connection.execute_write(
            """
            UPDATE users
            SET referred_by_user_id = ?, pending_referrer_id = NULL
            WHERE id = ? AND referred_by_user_id IS NULL
            """,
            (referrer_id, user_id),
        )

    async def list_referred_by(self, referrer_id: int) -> list[User]:
        """
        Every user permanently attributed to this referrer, regardless
        of which campaign finalized them — for reward reconciliation
        (see ReferralService.reconcile_pending_rewards).
        """
        rows = await self._connection.fetch_all(
            "SELECT * FROM users WHERE referred_by_user_id = ?", (referrer_id,)
        )
        return [_row_to_user(row) for row in rows]

    async def count_all(self) -> int:
        raise NotImplementedError
