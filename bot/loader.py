"""
Builds the core aiogram Bot and Dispatcher instances and wires together
every feature router.

This is the single place that knows about every handler module —
handler modules themselves stay decoupled from each other.

AdminGuardMiddleware is wired onto every admin router below — it's the
sole authorization gate for the admin panel. ErrorHandlerMiddleware,
ThrottlingMiddleware, and UserTrackingMiddleware are registered
globally, on every message/callback_query, in that order (error
boundary outermost so it can catch a failure anywhere below it;
throttling next so a spammed update never reaches the database;
user tracking last so it only runs for updates that survive both).
"""

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import settings
from bot.middlewares.admin_guard import AdminGuardMiddleware
from bot.middlewares.error_handler import ErrorHandlerMiddleware
from bot.middlewares.throttling import ThrottlingMiddleware
from bot.middlewares.user_tracking import UserTrackingMiddleware
from bot.services.referral_reward_handlers import CAMPAIGN_TYPE, GiveawayEntryRewardHandler
from bot.services.referral_service import register_reward_handler

# Handler routers (user-facing)
from bot.handlers.user import start, menu, tickets, referral, profile, participate

# Handler routers (admin-facing, Telegram-native inline panel)
from bot.handlers.admin import (
    panel,
    datetime_picker,
    giveaways as admin_giveaways,
    giveaway_manage,
    stats,
    users,
    required_channels,
    settings as admin_settings,
)


def create_bot() -> Bot:
    """Creates the aiogram Bot instance with default HTML parse mode."""
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    """
    Creates the Dispatcher and includes every feature router.

    FSM storage is in-process MemoryStorage — acceptable for a single-
    VPS, single-process deployment (see architecture doc, section 10 —
    Future Scalability — for when this would need to move to Redis).

    Every router is registered up front, even though most handlers are
    still empty stubs: this keeps the routing surface stable as
    business logic is filled in incrementally, without further changes
    to this file.
    """
    dp = Dispatcher(storage=MemoryStorage())

    # Plugs the giveaway-entry reward rule into the (campaign-agnostic)
    # referral engine. A future campaign registers its own handler here
    # under a new campaign_type — bot/services/referral_service.py never
    # needs to change.
    register_reward_handler(CAMPAIGN_TYPE, GiveawayEntryRewardHandler())

    # Global error boundary — registered on the Dispatcher itself so it
    # wraps every router's middleware and handlers, admin included.
    error_handler = ErrorHandlerMiddleware()
    dp.message.outer_middleware(error_handler)
    dp.callback_query.outer_middleware(error_handler)

    throttling = ThrottlingMiddleware()
    dp.message.outer_middleware(throttling)
    dp.callback_query.outer_middleware(throttling)

    user_tracking = UserTrackingMiddleware()
    dp.message.outer_middleware(user_tracking)
    dp.callback_query.outer_middleware(user_tracking)

    # User-facing routers
    dp.include_router(start.router)
    dp.include_router(menu.router)
    dp.include_router(participate.router)
    dp.include_router(tickets.router)
    dp.include_router(referral.router)
    dp.include_router(profile.router)

    # Admin-facing routers — gated by AdminGuardMiddleware, the sole
    # authorization check for the entire admin panel.
    admin_routers = (
        panel.router,
        admin_giveaways.router,
        datetime_picker.router,
        giveaway_manage.router,
        stats.router,
        users.router,
        required_channels.router,
        admin_settings.router,
    )
    for admin_router in admin_routers:
        admin_router.message.outer_middleware(AdminGuardMiddleware())
        admin_router.callback_query.outer_middleware(AdminGuardMiddleware())
        dp.include_router(admin_router)

    return dp
