from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Меню")]
        ],
        resize_keyboard=True
    )