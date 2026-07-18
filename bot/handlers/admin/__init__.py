"""
Admin-facing handlers — the entire Telegram-native admin panel.

/admin is the only slash command; every action after that is driven by
inline keyboard callbacks (callback_data prefixed "admin:"). Access is
gated by AdminGuardMiddleware, applied to these routers in bot/loader.py.
"""
