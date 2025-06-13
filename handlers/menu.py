# bot/handlers/menu.py
from aiogram import Router
from aiogram.types import CallbackQuery, Message
from keyboards.inline import get_main_menu_keyboard

router = Router()

@router.message(lambda msg: msg.text == "/start")
async def cmd_start(message: Message):
    await message.answer("Главное меню:", reply_markup=get_main_menu_keyboard())

@router.callback_query(lambda call: call.data == "main_menu")
async def back_to_main_menu(call: CallbackQuery):
    await call.message.edit_text("Главное меню:", reply_markup=get_main_menu_keyboard())
    await call.answer()