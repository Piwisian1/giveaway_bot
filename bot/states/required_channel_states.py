"""
FSM state group for the admin required-channels "Add Channel" prompt
(bot/handlers/admin/required_channels.py).
"""

from aiogram.fsm.state import State, StatesGroup


class RequiredChannelAdd(StatesGroup):
    waiting_for_channel = State()
