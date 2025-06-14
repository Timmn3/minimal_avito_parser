from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Меню")],
            [KeyboardButton(text="Запуск задач")]
        ],
        resize_keyboard=True
    )