from aiogram.fsm.state import State, StatesGroup


class SettingsForm(StatesGroup):
    restart_minutes = State()
    queue_step = State()
