import sqlite3

conn = sqlite3.connect("data/bot.db")
cur = conn.cursor()

print("=== REQUIRED CHANNELS ===")
for row in cur.execute(
    "SELECT id, telegram_chat_id, title, username, invite_link FROM required_channels"
):
    print(row)

conn.close()