"""
Editable seed list for the required-channels gate (see
bot/db/repositories/required_channel_repo.py) — edit this list to add
or change the channels a user must join to participate, then restart
the bot.

Used once, at startup: bot/db/seed.py inserts these rows into the
required_channels table only if that table is still empty. From then
on the database is the live source of truth — channels are added,
edited, or removed from the Telegram admin panel (/admin -> Required
Channels) with changes taking effect immediately, no restart needed.
So editing this file after the first run has no effect unless the
table is emptied first.

Fields:
  username     - public "@username" without the "@", or None for a
                 private/invite-only channel.
  chat_id      - the channel's numeric Telegram chat id (get it from
                 @userinfobot, or from bot logs after adding the bot
                 to the channel as an admin).
  invite_link  - the https://t.me/... link shown on the join button;
                 required when username is None.
  display_name - text shown to users, on the join button and on the
                 "still missing" screen.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RequiredChannelConfig:
    username: str | None
    chat_id: int
    invite_link: str | None
    display_name: str


REQUIRED_CHANNELS: list[RequiredChannelConfig] = [
    # Example — replace with your real channels:
    # RequiredChannelConfig(
    #     username="your_channel",
    #     chat_id=-1001234567890,
    #     invite_link="https://t.me/your_channel",
    #     display_name="Our Announcements Channel",
    # ),
]
