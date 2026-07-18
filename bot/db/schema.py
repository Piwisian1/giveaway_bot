"""
Idempotent schema definition for V1 — no migration system. All tables
are created with CREATE TABLE IF NOT EXISTS on every startup. If the
schema needs to change later, this project will introduce a proper
versioned migration system at that point (see architecture doc,
section 10 — Future Scalability).
"""

SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE NOT NULL,
        username TEXT,
        first_name TEXT,
        language_code TEXT,
        referral_code TEXT UNIQUE,
        referred_by_user_id INTEGER REFERENCES users(id),
        pending_referrer_id INTEGER REFERENCES users(id),
        is_banned INTEGER NOT NULL DEFAULT 0,
        is_admin INTEGER NOT NULL DEFAULT 0,
        joined_at TEXT NOT NULL DEFAULT (datetime('now')),
        last_seen_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS giveaways (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        first_prize TEXT,
        second_prize TEXT,
        third_prize TEXT,
        bonus_prize TEXT,
        start_at TEXT,
        end_at TEXT,
        is_active INTEGER NOT NULL DEFAULT 0
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS giveaway_required_channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        giveaway_id INTEGER NOT NULL REFERENCES giveaways(id),
        chat_id INTEGER NOT NULL,
        chat_username TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        giveaway_id INTEGER NOT NULL REFERENCES giveaways(id),
        user_id INTEGER NOT NULL REFERENCES users(id),
        tickets INTEGER NOT NULL DEFAULT 1,
        entered_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(giveaway_id, user_id)
    );
    """,
    """
    -- Reward ledger, deliberately generic: campaign_type/campaign_id
    -- describe *what* the referral was for (today: campaign_type=
    -- 'giveaway_entry', campaign_id=a giveaway id) and reward_type/
    -- reward_amount describe *what was granted* (today: 'ticket', 1).
    -- A future campaign needs a new campaign_type value, not a schema
    -- change. "Who invited whom" lives on users.referred_by_user_id
    -- instead — that relationship is permanent and campaign-independent,
    -- while a referral can earn a separate reward per campaign here.
    CREATE TABLE IF NOT EXISTS referral_rewards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        referrer_id INTEGER NOT NULL REFERENCES users(id),
        referred_id INTEGER NOT NULL REFERENCES users(id),
        campaign_type TEXT NOT NULL,
        campaign_id INTEGER,
        reward_type TEXT NOT NULL,
        reward_amount INTEGER NOT NULL DEFAULT 1,
        status TEXT NOT NULL DEFAULT 'granted',
        granted_at TEXT NOT NULL DEFAULT (datetime('now')),
        revoked_at TEXT,
        UNIQUE(referrer_id, referred_id, campaign_type, campaign_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS winners (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        giveaway_id INTEGER NOT NULL REFERENCES giveaways(id),
        user_id INTEGER NOT NULL REFERENCES users(id),
        position INTEGER NOT NULL,
        drawn_at TEXT NOT NULL DEFAULT (datetime('now')),
        notified INTEGER NOT NULL DEFAULT 0
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS admin_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER NOT NULL REFERENCES users(id),
        action TEXT NOT NULL,
        target TEXT,
        details TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS required_channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_chat_id INTEGER NOT NULL,
        username TEXT,
        title TEXT NOT NULL,
        invite_link TEXT,
        sort_order INTEGER NOT NULL DEFAULT 0,
        is_active INTEGER NOT NULL DEFAULT 1
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_entries_giveaway ON entries(giveaway_id);",
    "CREATE INDEX IF NOT EXISTS idx_entries_user ON entries(user_id);",
    # Partial unique index: enforces "only one giveaway can be active" at
    # the database level, on top of the application-level check in
    # GiveawayRepository.activate().
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_giveaways_single_active "
    "ON giveaways(is_active) WHERE is_active = 1;",
    "CREATE INDEX IF NOT EXISTS idx_referral_rewards_referrer ON referral_rewards(referrer_id);",
    "CREATE INDEX IF NOT EXISTS idx_referral_rewards_referred ON referral_rewards(referred_id);",
    "CREATE INDEX IF NOT EXISTS idx_referral_rewards_campaign ON referral_rewards(campaign_type, campaign_id);",
    "CREATE INDEX IF NOT EXISTS idx_required_channels_active_sort ON required_channels(is_active, sort_order);",
)


async def init_schema() -> None:
    """Applies every CREATE TABLE/INDEX statement against the shared connection."""
    from bot.db.connection import get_connection

    connection = get_connection()
    for statement in SCHEMA_STATEMENTS:
        await connection.execute_write(statement)
