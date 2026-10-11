from aiogram import Router
from aiogram.types import CallbackQuery, Message
from config import ADMIN_IDS
from keyboards.inline import get_main_menu_keyboard, get_back_button
from utils.formatting import get_help_text

router = Router()

@router.message(lambda msg: msg.text == "/menu")
@router.message(lambda msg: msg.text == "Меню")
async def cmd_start(message: Message):
    await message.answer("Выберите действие:",
                         reply_markup=get_main_menu_keyboard(message.from_user.id in ADMIN_IDS))

@router.callback_query(lambda call: call.data == "main_menu")
async def show_main_menu(call: CallbackQuery):
    await call.message.edit_text("Главное меню:",
                                 reply_markup=get_main_menu_keyboard(call.from_user.id in ADMIN_IDS))
    await call.answer()

@router.callback_query(lambda call: call.data == "help")
async def show_help(call: CallbackQuery):
    await call.message.edit_text(get_help_text(), reply_markup=get_back_button(), parse_mode="HTML")
    await call.answer()

@router.message(lambda msg: msg.text == "/help")
async def show_help(message: Message):
    await message.answer(get_help_text(), reply_markup=get_back_button(), parse_mode="HTML")
