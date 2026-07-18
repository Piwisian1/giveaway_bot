"""
Lightweight asyncio-based periodic tasks — the replacement for
APScheduler. Each task is a simple `while True: ... ; await asyncio.sleep(...)`
loop, started once from run.py and cancelled on shutdown. No external
scheduling dependency required.
"""
