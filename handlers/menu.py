from aiogram import Router
from aiogram.types import CallbackQuery, Message
from keyboards.inline import get_main_menu_keyboard, get_back_button

router = Router()

@router.message(lambda msg: msg.text == "/start")
async def cmd_start(message: Message):
    await message.answer("Главное меню:", reply_markup=get_main_menu_keyboard())

@router.callback_query(lambda call: call.data == "main_menu")
async def show_main_menu(call: CallbackQuery):
    await call.message.edit_text("Главное меню:", reply_markup=get_main_menu_keyboard())
    await call.answer()

@router.callback_query(lambda call: call.data == "help")
async def show_help(call: CallbackQuery):
    await call.message.edit_text(get_help_text(), reply_markup=get_back_button())
    await call.answer()

@router.callback_query(lambda call: call.data == "settings")
async def show_settings(call: CallbackQuery):
    text = "⚙️ Настройки:\n\n" \
           "• Включение/отключение уведомлений\n" \
           "• Изменение частоты парсинга\n" \
           "• Рассылка только новых объявлений"
    await call.message.edit_text(text, reply_markup=get_back_button())
    await call.answer()

@router.callback_query(lambda call: call.data == "view_ads")
async def show_new_ads(call: CallbackQuery):
    from parsing.parser_avito import seen_ads
    if not seen_ads:
        await call.message.edit_text("Нет новых объявлений.", reply_markup=get_back_button())
        return

    for ad_id, (name, price, link) in seen_ads.items():
        await call.message.answer(
            f"📍 {name}\n"
            f"{price}\n"
            f"{link}"
        )

    await call.message.edit_text("Последние объявления:", reply_markup=get_back_button())
    await call.answer()