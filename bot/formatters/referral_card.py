"""
Builds the text for the "Invite Friends" screen: the user's personal
referral link plus their referral stats. Stats are a plain read of the
existing referral_rewards ledger (see
bot/db/repositories/referral_repo.py::get_stats_for_referrer) — no
separate tracking, no admin-facing leaderboard here.
"""

from bot.db.repositories.referral_repo import ReferralStats
from bot.utils.formatting import escape_html, pluralize


def render_invite_screen(link: str, stats: ReferralStats) -> str:
    friend_word = pluralize(stats.successful_referrals, "friend", "friends")
    entry_word = pluralize(stats.entries_earned, "entry", "entries")
    return (
        "👥 <b>Invite Friends</b>\n"
        "<i>Share your link — earn bonus entries for every friend who joins.</i>\n\n"
        f"<code>{escape_html(link)}</code>\n\n"
        f"🤝 <b>{stats.successful_referrals}</b> {friend_word} joined\n"
        f"🎟 <b>{stats.entries_earned}</b> bonus {entry_word} earned"
    )
