"""
Static message copy (English). Kept separate from bot/formatters/ so
that adding a language later is additive (a new texts/<lang>.py file),
not structural.
"""

# Shown to the user by ErrorHandlerMiddleware instead of leaking exceptions
GENERIC_ERROR = "Something went wrong. Please try again."

# Root of the Telegram-native admin panel (see bot/handlers/admin/panel.py)
ADMIN_MENU = "🛠 <b>Admin Panel</b>\n<i>Manage giveaways, channels, and users.</i>"

# Required-channels admin screen (see bot/handlers/admin/required_channels.py)
ADD_CHANNEL_PROMPT = "📢 Send the channel username (example: @PWNews) or invite link."
ADD_CHANNEL_SUCCESS = "✅ Added <b>{title}</b> to the required channels."

# Giveaway creation wizard (see bot/handlers/admin/giveaways.py). Every
# step but title/first_prize/end_at accepts "-" to skip. start_at/end_at
# are picked via the inline calendar (see DATETIME_PICK_* below and
# bot/handlers/admin/datetime_picker.py), never typed.
GIVEAWAY_CREATE_PROMPTS = {
    "title": "🎁 Send the giveaway title.",
    "description": "📝 Send a description, or send - to skip.",
    "first_prize": "🏆 Send the 1st place prize.",
    "second_prize": "🥈 Send the 2nd place prize, or send - to skip.",
    "third_prize": "🥉 Send the 3rd place prize, or send - to skip.",
    "bonus_prize": "🎉 Send the bonus prize, or send - to skip.",
}
GIVEAWAY_CREATE_SUCCESS = "✅ Created <b>{title}</b>. It's inactive until you tap Activate Giveaway."
GIVEAWAY_REQUIRED_FIELD_ERROR = "This field can't be empty. Send a value."
GIVEAWAY_EDIT_FIELD_PROMPT = "Send the new value for {field}, or - to clear it."
# Used instead of GIVEAWAY_EDIT_FIELD_PROMPT for title/first_prize/end_at —
# required fields the edit flow won't let an admin blank out (see
# bot/handlers/admin/giveaways.py::_REQUIRED_FIELDS).
GIVEAWAY_EDIT_REQUIRED_FIELD_PROMPT = "Send the new value for {field}. This field can't be cleared."
GIVEAWAY_EDIT_SUCCESS = "✅ Updated {field}."

# Inline calendar/hour/minute picker (see
# bot/handlers/admin/datetime_picker.py) — the only way to set
# start_at/end_at, in both the creation wizard and the edit flow. Every
# value produced is UTC, matching the storage format used everywhere
# else (GiveawayRepository, the auto-closer's datetime('now') compares).
DATETIME_PICK_CALENDAR_CAPTION = "📅 Pick the {field} (UTC)."
DATETIME_PICK_HOUR_CAPTION = "🕐 Pick the hour (UTC).\nDate: {date}"
DATETIME_PICK_MINUTE_CAPTION = "🕐 Pick the minute (UTC).\nDate: {date} {hour}:--"
DATETIME_PICK_USE_BUTTONS = "Please use the buttons above to pick a date/time."
# Plain text (no HTML) — shown as a callback answerCallbackQuery toast, which
# doesn't render markup.
GIVEAWAY_DELETE_SUCCESS = "Deleted {title}."
GIVEAWAY_ACTIVATE_SUCCESS = "{title} is now the active giveaway."

# Sent by DM to each winner once bot/services/winner_service.py draws them.
WINNER_NOTIFICATION = (
    "🏆 <b>You won!</b>\n\n"
    "Congratulations — you're the winner of <b>{prize}</b> in \"{title}\"!\n\n"
    "An admin will be in touch with you about your prize."
)

# Giveaway lifecycle management (see bot/handlers/admin/giveaway_manage.py).
# Plain text (no HTML) — every one of these is shown as a callback
# answerCallbackQuery toast, which doesn't render markup.
GIVEAWAY_END_SUCCESS = "{title} ended. {count} winner(s) drawn."
GIVEAWAY_END_NO_WINNERS = "{title} ended. No eligible entrants — no winners drawn."
GIVEAWAY_CANCEL_SUCCESS = "{title} cancelled. No winners were drawn."
GIVEAWAY_REROLL_SUCCESS = "Rerolled {count} winner(s)."
GIVEAWAY_REROLL_NO_WINNERS = "Rerolled — no eligible entrants remained, so no winners were drawn."
GIVEAWAY_NOT_ACTIVE_ERROR = "That giveaway isn't active."
GIVEAWAY_NOT_ENDED_ERROR = "That giveaway hasn't ended yet."
GIVEAWAY_ALREADY_DRAWN_ERROR = "That giveaway already had winners drawn — it can't be reactivated."
