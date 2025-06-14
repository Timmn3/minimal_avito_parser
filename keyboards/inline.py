from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 Мои задачи", callback_data="my_tasks"),
        InlineKeyboardButton(text="➕ Добавить задачу", callback_data="add_task")
    )
    builder.row(
        InlineKeyboardButton(text="❓ Помощь", callback_data="help")
    )
    return builder.as_markup()

def get_task_actions_keyboard(task_id=None):
    builder = InlineKeyboardBuilder()
    if task_id:
        builder.row(
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_task_{task_id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_task_{task_id}")
        )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="my_tasks"),
        InlineKeyboardButton(text="↩️ Главное меню", callback_data="main_menu")
    )
    return builder.as_markup()

def get_back_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
    ])

def get_cancel():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✖️ Отменить", callback_data="main_menu")]
    ])

def run_task(task_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Запустить задачу", callback_data=f"run_task_{task_id}")]
    ])
