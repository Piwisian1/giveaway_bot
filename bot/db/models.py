"""
Lightweight row-mapping dataclasses mirroring the schema in
bot/db/schema.py. Repositories return these instead of raw sqlite
Row/tuple objects.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class User:
    id: int
    telegram_id: int
    username: str | None
    first_name: str | None
    language_code: str | None
    referral_code: str | None
    referred_by_user_id: int | None
    pending_referrer_id: int | None
    is_banned: bool
    is_admin: bool
    joined_at: str
    last_seen_at: str


@dataclass(slots=True)
class Giveaway:
    """
    A single giveaway. Only one row may have is_active=True at a time
    (enforced by a partial unique index — see bot/db/schema.py) — this
    project does not support multiple concurrent active giveaways.
    """

    id: int
    title: str
    description: str | None
    first_prize: str | None
    second_prize: str | None
    third_prize: str | None
    bonus_prize: str | None
    start_at: str | None
    end_at: str | None
    is_active: bool


@dataclass(slots=True)
class GiveawayRequiredChannel:
    id: int
    giveaway_id: int
    chat_id: int
    chat_username: str | None


@dataclass(slots=True)
class Entry:
    id: int
    giveaway_id: int
    user_id: int
    tickets: int
    entered_at: str


@dataclass(slots=True)
class ReferralReward:
    """
    A single reward payout for a referral, scoped to one campaign. The
    referral *relationship* itself lives on User.referred_by_user_id
    instead — permanent and campaign-independent. campaign_type/
    campaign_id/reward_type are free-form by design (see
    bot/services/referral_service.py) so a future campaign needs a new
    campaign_type value, not a schema change.
    """

    id: int
    referrer_id: int
    referred_id: int
    campaign_type: str
    campaign_id: int | None
    reward_type: str
    reward_amount: int
    status: str
    granted_at: str
    revoked_at: str | None


@dataclass(slots=True)
class Winner:
    id: int
    giveaway_id: int
    user_id: int
    position: int
    drawn_at: str
    notified: bool


@dataclass(slots=True)
class AdminLog:
    id: int
    admin_id: int
    action: str
    target: str | None
    details: str | None
    created_at: str


@dataclass(slots=True)
class RequiredChannel:
    """
    A channel a user must join to participate — global, not tied to a
    specific giveaway. Distinct from GiveawayRequiredChannel, which is
    part of the (untouched) per-giveaway required-channels concept.
    """

    id: int
    telegram_chat_id: int
    username: str | None
    title: str
    invite_link: str | None
    sort_order: int
    is_active: bool
