from aiogram.fsm.state import State, StatesGroup

class TaskForm(StatesGroup):
    number = State()
    teg = State()
    url = State()
    time_repeat = State()
    count_page = State()
    target_words = State()
    stop_words = State()
    max_ads_per_run = State()
    min_price = State()
    max_price = State()
    activity = State()
    price_change = State()
    all_ads = State()