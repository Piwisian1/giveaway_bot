# Telegram Giveaway Bot

Production-oriented Telegram giveaway bot. Stack: Python 3.14, aiogram 3,
SQLite (via aiosqlite), python-dotenv. Single VPS deployment, admin panel
entirely inside Telegram (inline menus, no separate web dashboard).

Feature-complete for V1 and manually tested end to end: giveaway
creation/edit (inline calendar date/time picker)/activation, the join
flow with required-channel gating, automatic and manual winner
selection, referrals, and the full admin lifecycle panel. A few
secondary screens (My Tickets, Profile stats, admin Users/Stats/Settings)
are still placeholders — see the TODOs in `bot/handlers/`.

## Structure

See inline comments in each module. High-level layout:

- `bot/handlers/` — thin Telegram-facing routers (user + admin)
- `bot/middlewares/` — cross-cutting concerns (db session, throttling, auth, errors)
- `bot/services/` — business logic, DB-agnostic
- `bot/db/` — SQLite connection + schema + repositories
- `bot/background/` — asyncio-based periodic tasks (live updates, auto-close)
- `bot/keyboards/`, `bot/texts/`, `bot/formatters/` — presentation layer
- `bot/states/` — FSM state groups
- `bot/utils/` — formatting, validation, security helpers

## Setup

1. `python -m venv venv` (already present) then activate it.
2. `pip install -r requirements.txt`
3. `cp .env.example .env` and fill in `BOT_TOKEN` and `ADMIN_IDS`.
4. `python run.py`
5. `chmod +x scripts/backup_db.sh`, then schedule it via cron — e.g.
   `0 */6 * * * /opt/giveaway-bot/scripts/backup_db.sh >> /opt/giveaway-bot/logs/backup.log 2>&1`
   for a snapshot every 6 hours. SQLite is the bot's only datastore; without
   this step there is no backup.

## Design notes

- **No Redis/PostgreSQL** — SQLite is the only datastore, using WAL mode
  and a single-writer queue (`bot/db/connection.py`) to stay safe under
  concurrent access from aiogram's handlers.
- **No APScheduler** — periodic work (live-updating giveaway messages,
  auto-closing ended giveaways) runs as plain `asyncio` background loops
  in `bot/background/`.
- **No migration system in V1** — `bot/db/schema.py` applies
  `CREATE TABLE IF NOT EXISTS` on every startup. A versioned migration
  system will be introduced only if/when the schema needs to evolve
  post-launch.
- **Broadcast messaging is out of scope for V1.**
- **Admin panel is 100% inline-menu driven** — `/admin` is the only
  admin command; every action after that is a callback button.
- **Multiple concurrent giveaways are a first-class concept** — nothing
  in the schema or services assumes a single active giveaway.
