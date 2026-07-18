"""
Reward handlers are the only place campaign-specific referral rules
live — bot/services/referral_service.py is deliberately generic and
knows nothing about giveaways or tickets. This module has exactly one
handler today: converting a referral into bonus giveaway tickets. A
future campaign (a different reward, a non-giveaway campaign) adds a
new handler here (or in its own module) and registers it in
bot/loader.py — nothing in the referral engine itself changes.
"""

from bot.db.connection import get_connection
from bot.db.repositories.entry_repo import EntryRepository
from bot.services.referral_service import RewardOutcome

# The campaign_type string that identifies this handler to the engine.
# Shared by bot/loader.py (registration) and
# bot/handlers/user/participate.py (the conversion trigger) so the
# string is defined in exactly one place.
CAMPAIGN_TYPE = "giveaway_entry"

# TODO (admin settings milestone): read from the settings table instead
# of this constant, so the reward amount is admin-configurable without
# a deploy.
_ENTRY_REWARD_AMOUNT = 1


class GiveawayEntryRewardHandler:
    """
    Rewards a referrer with bonus giveaway entries when their invite
    converts into a verified giveaway entry — but only for a giveaway
    the referrer has already joined themselves. Registered under
    CAMPAIGN_TYPE; campaign_id is the giveaway's id.
    """

    async def grant(self, referrer_id: int, referred_id: int, campaign_id: int | None) -> RewardOutcome | None:
        if campaign_id is None:
            return None

        entry_repo = EntryRepository(get_connection())
        if await entry_repo.get(campaign_id, referrer_id) is None:
            return None  # referrer hasn't joined this giveaway themselves — no reward
        if await entry_repo.get(campaign_id, referred_id) is None:
            # Self-contained rather than trusting the caller: this handler
            # is now invoked from two directions (see
            # bot/services/referral_service.py::reconcile_pending_rewards,
            # which checks every historically-referred user, not just
            # ones who entered *this* giveaway), so it must verify both
            # sides itself rather than assuming the referred user's entry
            # in this specific campaign_id.
            return None

        amount = _ENTRY_REWARD_AMOUNT
        await entry_repo.add_tickets(campaign_id, referrer_id, amount)
        unit = "entry" if amount == 1 else "entries"
        return RewardOutcome(
            reward_type="ticket",
            reward_amount=amount,
            description=f"+{amount} giveaway {unit} added.",
        )
