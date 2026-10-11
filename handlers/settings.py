from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select

from config import ADMIN_IDS
from database.db import async_session
from database.models import Task
from keyboards.inline import get_settings_keyboard, get_settings_cancel
from parsing.parser_avito import MIN_REQUEST_INTERVAL
from services import settings_service as cfg
from states.settings_states import SettingsForm

router = Router()

NO_RIGHTS = "Недостаточно прав"


async def settings_text() -> str:
    s = await cfg.get_queue_settings()
    async with async_session() as session:
        active = (await session.execute(
            select(func.count()).select_from(Task).where(Task.activity.is_(True)))).scalar() or 0

    restart = s["restart_minutes"]
    restart_text = f"каждые {restart} мин" if restart else "не перезапускать"
    step = s["queue_step"]
    # каждая задача проверяется не чаще раза в MIN_REQUEST_INTERVAL, а при большом числе задач - раз в active*step
    per_task = max(MIN_REQUEST_INTERVAL, active * step)
    return (
        "⚙️ <b>Настройки</b>\n\n"
        f"🔄 Перезапуск браузера: <b>{restart_text}</b>\n"
        f"⏱ Шаг очереди: <b>{step} сек</b> (пауза между любыми запросами к Авито)\n"
        f"🔁 Режим загрузки: <b>{cfg.LOAD_MODE_TITLES[s['load_mode']]}</b>\n\n"
        f"📋 Активных задач: {active}\n"
        f"Каждая задача проверяется примерно раз в <b>{per_task} сек</b>\n"
        "<i>(не чаще раза в минуту и не чаще, чем указано в её интервале)</i>"
    )


@router.message(Command("settings"))
async def cmd_settings(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer(NO_RIGHTS)
        return
    await state.clear()
    await message.answer(await settings_text(), parse_mode="HTML", reply_markup=get_settings_keyboard())


@router.callback_query(lambda call: call.data == "settings")
async def show_settings(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer(NO_RIGHTS, show_alert=True)
        return
    await state.clear()
    await call.message.edit_text(await settings_text(), parse_mode="HTML", reply_markup=get_settings_keyboard())
    await call.answer()


@router.callback_query(lambda call: call.data == "set_restart")
async def ask_restart(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer(NO_RIGHTS, show_alert=True)
        return
    await state.set_state(SettingsForm.restart_minutes)
    await call.message.edit_text(
        f"Через сколько <b>минут</b> перезапускать браузер ({cfg.MIN_RESTART_MINUTES}-{cfg.MAX_RESTART_MINUTES}).\n"
        "<b>0</b> - не перезапускать.\n\n"
        "<i>Свежий браузер при первом заходе чаще получает заглушку Авито, поэтому реже - спокойнее.</i>",
        parse_mode="HTML", reply_markup=get_settings_cancel())
    await call.answer()


@router.message(SettingsForm.restart_minutes)
async def process_restart(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await state.clear()
        await message.answer(NO_RIGHTS)
        return
    text = (message.text or "").strip()
    if not text.isdigit() or not cfg.validate_restart_minutes(int(text)):
        await message.answer(f"Введите 0 или число от {cfg.MIN_RESTART_MINUTES} до {cfg.MAX_RESTART_MINUTES}:",
                             reply_markup=get_settings_cancel())
        return
    await cfg.save_restart_minutes(int(text))
    await state.clear()
    await message.answer("✅ Сохранено\n\n" + await settings_text(), parse_mode="HTML",
                         reply_markup=get_settings_keyboard())


@router.callback_query(lambda call: call.data == "set_mode")
async def switch_mode(call: CallbackQuery, state: FSMContext):
    """Переключает режим загрузки страницы по кругу; парсер подхватывает на следующем шаге."""
    if call.from_user.id not in ADMIN_IDS:
        await call.answer(NO_RIGHTS, show_alert=True)
        return
    await state.clear()
    new_mode = await cfg.cycle_load_mode()
    await call.message.edit_text(await settings_text(), parse_mode="HTML", reply_markup=get_settings_keyboard())
    await call.answer(f"Режим: {cfg.LOAD_MODE_TITLES[new_mode]}")


@router.callback_query(lambda call: call.data == "set_step")
async def ask_step(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer(NO_RIGHTS, show_alert=True)
        return
    await state.set_state(SettingsForm.queue_step)
    await call.message.edit_text(
        f"Шаг очереди в <b>секундах</b> ({cfg.MIN_QUEUE_STEP}-{cfg.MAX_QUEUE_STEP}): пауза между любыми двумя "
        "запросами к Авито, включая обновления при заглушке.\n\n"
        "<i>Меньше - быстрее проверка задач, но выше риск бана по IP.</i>",
        parse_mode="HTML", reply_markup=get_settings_cancel())
    await call.answer()


@router.message(SettingsForm.queue_step)
async def process_step(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await state.clear()
        await message.answer(NO_RIGHTS)
        return
    text = (message.text or "").strip()
    if not text.isdigit() or not cfg.validate_queue_step(int(text)):
        await message.answer(f"Введите число от {cfg.MIN_QUEUE_STEP} до {cfg.MAX_QUEUE_STEP}:",
                             reply_markup=get_settings_cancel())
        return
    await cfg.save_queue_step(int(text))
    await state.clear()
    await message.answer("✅ Сохранено\n\n" + await settings_text(), parse_mode="HTML",
                         reply_markup=get_settings_keyboard())
