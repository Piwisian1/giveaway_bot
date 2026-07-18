"""
Data access for the referral_rewards ledger. The referral
*relationship* (who invited whom) lives on users.referred_by_user_id
instead — see bot/db/repositories/user_repo.py — so this repository is
only concerned with individual reward payouts, one row per
(referrer, referred, campaign).
"""

from dataclasses import dataclass

from bot.db.connection import DatabaseConnection
from bot.db.models import ReferralReward


@dataclass(slots=True)
class ReferralStats:
    """Aggregate view over a referrer's granted rewards — not a schema row, computed on read."""

    successful_referrals: int
    entries_earned: int


def _row_to_reward(row: dict) -> ReferralReward:
    return ReferralReward(
        id=row["id"],
        referrer_id=row["referrer_id"],
        referred_id=row["referred_id"],
        campaign_type=row["campaign_type"],
        campaign_id=row["campaign_id"],
        reward_type=row["reward_type"],
        reward_amount=row["reward_amount"],
        status=row["status"],
        granted_at=row["granted_at"],
        revoked_at=row["revoked_at"],
    )


class ReferralRewardRepository:
    def __init__(self, connection: DatabaseConnection) -> None:
        self._connection = connection

    async def get(
        self, referrer_id: int, referred_id: int, campaign_type: str, campaign_id: int | None
    ) -> ReferralReward | None:
        """Looks up an existing reward for this exact (referrer, referred, campaign) triple, if any."""
        row = await self._connection.fetch_one(
            """
            SELECT * FROM referral_rewards
            WHERE referrer_id = ? AND referred_id = ? AND campaign_type = ?
                AND campaign_id IS ?
            """,
            (referrer_id, referred_id, campaign_type, campaign_id),
        )
        return _row_to_reward(row) if row is not None else None

    async def create(
        self,
        referrer_id: int,
        referred_id: int,
        campaign_type: str,
        campaign_id: int | None,
        reward_type: str,
        reward_amount: int,
    ) -> ReferralReward:
        """Idempotent via UNIQUE(referrer_id, referred_id, campaign_type, campaign_id) — conflicts are silently ignored."""
        await self._connection.execute_write(
            """
            INSERT INTO referral_rewards
                (referrer_id, referred_id, campaign_type, campaign_id, reward_type, reward_amount)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(referrer_id, referred_id, campaign_type, campaign_id) DO NOTHING
            """,
            (referrer_id, referred_id, campaign_type, campaign_id, reward_type, reward_amount),
        )
        reward = await self.get(referrer_id, referred_id, campaign_type, campaign_id)
        assert reward is not None
        return reward

    async def revoke(self, reward_id: int) -> None:
        """Marks a reward revoked (fraud claw-back) — see the (future) admin revoke action."""
        raise NotImplementedError

    async def get_stats_for_referrer(self, referrer_id: int) -> ReferralStats:
        """
        Returns how many successful (granted, non-revoked) referrals this
        user has, and how many giveaway entries they've earned from them.
        Scoped to reward_type='ticket' so a future non-entry reward type
        wouldn't be miscounted as giveaway entries.
        """
        row = await self._connection.fetch_one(
            """
            SELECT COUNT(*) AS successful_referrals, COALESCE(SUM(reward_amount), 0) AS entries_earned
            FROM referral_rewards
            WHERE referrer_id = ? AND status = 'granted' AND reward_type = 'ticket'
            """,
            (referrer_id,),
        )
        return ReferralStats(
            successful_referrals=row["successful_referrals"],
            entries_earned=row["entries_earned"],
        )

    async def get_leaderboard(self, campaign_type: str, campaign_id: int | None, limit: int) -> list[tuple]:
        raise NotImplementedError
