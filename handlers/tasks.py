# bot/handlers/tasks.py
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from states.task_states import TaskForm
from keyboards.inline import get_task_actions_keyboard, get_back_button
from utils.formatting import format_task
from database.db import async_session, get_user_tasks, add_task, update_task, get_all_tasks

router = Router()

@router.message(lambda msg: msg.text == "/tasks")
async def show_user_tasks(message: Message):
    tasks = await get_all_tasks()
    if not tasks:
        await message.answer("Нет активных задач.")
        return

    for task in tasks:
        await message.answer(format_task(task), disable_web_page_preview=True)

@router.callback_query(lambda call: call.data == "my_tasks")
async def show_user_tasks(call: CallbackQuery):
    user_id = call.from_user.id
    async with async_session() as session:
        tasks = await get_user_tasks(session, user_id)

    if not tasks:
        await call.message.edit_text("У вас нет задач.", reply_markup=get_back_button())
        return

    for task in tasks:
        await call.message.answer(
            format_task(task),
            reply_markup=get_task_actions_keyboard(task.id)
        )

    await call.answer()


@router.callback_query(lambda call: call.data.startswith("edit_task_"))
async def edit_task_start(call: CallbackQuery, state: FSMContext):
    task_id = int(call.data.split("_")[2])
    await state.update_data(task_id=task_id)
    await call.message.edit_text("Введите новое значение для поля <b>номер задачи</b>:")
    await state.set_state(TaskForm.number)


@router.message(TaskForm.number)
async def process_number(message: Message, state: FSMContext):
    try:
        number = int(message.text)
        await state.update_data(number=number)
        await message.answer("Введите новое значение для поля <b>метка задачи (teg)</b>:")
        await state.set_state(TaskForm.teg)
    except ValueError:
        await message.answer("Неверный формат. Введите число:")


@router.message(TaskForm.teg)
async def process_teg(message: Message, state: FSMContext):
    await state.update_data(teg=message.text)
    await message.answer("Введите новое значение для поля <b>URL</b>:")
    await state.set_state(TaskForm.url)


@router.message(TaskForm.url)
async def process_url(message: Message, state: FSMContext):
    await state.update_data(url=message.text)
    await message.answer("Введите новое значение для поля <b>время повторения (минуты)</b>:")
    await state.set_state(TaskForm.time_repeat)


@router.message(TaskForm.time_repeat)
async def process_time_repeat(message: Message, state: FSMContext):
    try:
        time_repeat = int(message.text)
        await state.update_data(time_repeat=time_repeat)
        await message.answer("Введите новое значение для поля <b>количество страниц</b>:")
        await state.set_state(TaskForm.count_page)
    except ValueError:
        await message.answer("Неверный формат. Введите число:")


@router.message(TaskForm.count_page)
async def process_count_page(message: Message, state: FSMContext):
    try:
        count_page = int(message.text)
        await state.update_data(count_page=count_page)
        await message.answer("Введите новые ключевые слова (через запятую):")
        await state.set_state(TaskForm.target_words)
    except ValueError:
        await message.answer("Неверный формат. Введите число:")


@router.message(TaskForm.target_words)
async def process_target_words(message: Message, state: FSMContext):
    words = [w.strip() for w in message.text.split(",")] if message.text else []
    await state.update_data(target_words=words)
    await message.answer("Введите стоп-слова (через запятую):")
    await state.set_state(TaskForm.stop_words)


@router.message(TaskForm.stop_words)
async def process_stop_words(message: Message, state: FSMContext):
    words = [w.strip() for w in message.text.split(",")] if message.text else []
    await state.update_data(stop_words=words)
    await message.answer("Введите лимит объявлений за цикл:")
    await state.set_state(TaskForm.max_ads_per_run)


@router.message(TaskForm.max_ads_per_run)
async def process_max_ads(message: Message, state: FSMContext):
    try:
        max_ads = int(message.text)
        await state.update_data(max_ads_per_run=max_ads)
        await message.answer("Задача активна? (да/нет)")
        await state.set_state(TaskForm.activity)
    except ValueError:
        await message.answer("Неверный формат. Введите число:")


@router.message(TaskForm.activity)
async def process_activity(message: Message, state: FSMContext):
    text = message.text.lower()
    activity = True if text in ["да", "yes", "1", "true"] else False
    await state.update_data(activity=activity)
    await message.answer("Отслеживать изменение цены? (да/нет)")
    await state.set_state(TaskForm.price_change)


@router.message(TaskForm.price_change)
async def process_price_change(message: Message, state: FSMContext):
    text = message.text.lower()
    price_change = True if text in ["да", "yes", "1", "true"] else False
    await state.update_data(price_change=price_change)
    await message.answer("Отправлять все объявления? (да/нет)")
    await state.set_state(TaskForm.all_ads)


@router.message(TaskForm.all_ads)
async def process_all_ads(message: Message, state: FSMContext):
    text = message.text.lower()
    all_ads = True if text in ["да", "yes", "1", "true"] else False
    await state.update_data(all_ads=all_ads)

    data = await state.get_data()
    task_id = data.get("task_id")

    async with async_session() as session:
        await update_task(session, task_id, data)

    await message.answer("✅ Задача успешно обновлена!", reply_markup=get_back_button())
    await state.clear()


@router.callback_query(lambda call: call.data == "add_task")
async def start_add_task(call: CallbackQuery, state: FSMContext):
    await state.set_state(TaskForm.number)
    await call.message.edit_text("Введите значение для поля <b>номер задачи</b>:")
