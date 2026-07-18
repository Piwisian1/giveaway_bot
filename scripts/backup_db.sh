#!/usr/bin/env bash
# Checkpoints the SQLite WAL file and copies a timestamped snapshot of
# the database into data/backups/. Intended to be run via cron — see
# README.md's Setup section for the crontab line.
set -euo pipefail

# Resolve paths relative to this script's location, not the caller's cwd
# — cron doesn't run scripts from the project root, so a bare relative
# "data/bot.db" would silently look in the wrong place.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

DB_PATH="${DB_PATH:-$PROJECT_ROOT/data/bot.db}"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/data/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
TIMESTAMP="$(date -u +%Y%m%d_%H%M%S)"
BACKUP_FILE="$BACKUP_DIR/bot_${TIMESTAMP}.db"

mkdir -p "$BACKUP_DIR"

if [ ! -f "$DB_PATH" ]; then
    echo "backup_db.sh: no database at $DB_PATH yet, nothing to back up" >&2
    exit 0
fi

if ! command -v sqlite3 >/dev/null 2>&1; then
    echo "backup_db.sh: sqlite3 CLI not found on PATH" >&2
    exit 1
fi

# Merges the WAL into the main file first, so the file itself is a
# complete snapshot and doesn't grow unbounded between backups.
sqlite3 "$DB_PATH" "PRAGMA wal_checkpoint(TRUNCATE);"

# sqlite3's own `.backup` command uses SQLite's online backup API, which
# is safe to run even while the bot process is writing concurrently —
# unlike a plain `cp`, which could copy a torn, inconsistent file.
sqlite3 "$DB_PATH" ".backup '$BACKUP_FILE'"

# Prune backups older than the retention window.
find "$BACKUP_DIR" -name 'bot_*.db' -type f -mtime "+${RETENTION_DAYS}" -delete

echo "backup_db.sh: wrote $BACKUP_FILE"
