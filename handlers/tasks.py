from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from database.models import Task
from states.task_states import TaskForm
from keyboards.inline import get_task_actions_keyboard, get_back_button
from utils.formatting import format_task
from database.db import async_session, get_user_tasks, update_task, get_all_tasks

router = Router()

# === Клавиатура для пропуска шага ===
def skip_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➡️ Пропустить", callback_data="skip")]
    ])

# === Команда /tasks — вывод всех задач ===
@router.message(lambda msg: msg.text == "/tasks")
async def show_user_tasks(message: Message):
    tasks = await get_all_tasks()
    if not tasks:
        await message.answer("Нет активных задач.")
        return
    for task in tasks:
        await message.answer(format_task(task), disable_web_page_preview=True)

# === Кнопка "Мои задачи" ===
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

# === Начало редактирования задачи ===
@router.callback_query(lambda call: call.data.startswith("edit_task_"))
async def edit_task_start(call: CallbackQuery, state: FSMContext):
    task_id = int(call.data.split("_")[2])
    user_id = call.from_user.id

    async with async_session() as session:
        result = await session.execute(
            select(Task).where(Task.id == task_id, Task.user_id == user_id)
        )
        task = result.scalars().first()

        if not task:
            print(f"Создаём новую задачу {task_id} для пользователя {user_id}")
            task = Task(id=task_id, user_id=user_id)
            session.add(task)
            await session.flush()

    await state.update_data(task_id=task_id, user_id=user_id)
    await call.message.edit_text("Введите новое значение для поля <b>номер задачи</b>:", parse_mode="HTML")
    await state.set_state(TaskForm.number)

# === Ввод номера задачи ===
@router.message(TaskForm.number)
async def process_number(message: Message, state: FSMContext):
    try:
        number = int(message.text)
        await state.update_data(number=number)
        await message.answer("Введите новое значение для поля <b>метка задачи (teg)</b>:", parse_mode="HTML")
        await state.set_state(TaskForm.teg)
    except ValueError:
        await message.answer("Неверный формат. Введите число:")

# === Ввод метки задачи ===
@router.message(TaskForm.teg)
async def process_teg(message: Message, state: FSMContext):
    await state.update_data(teg=message.text)
    await message.answer("Введите новое значение для поля <b>URL</b>:", parse_mode="HTML")
    await state.set_state(TaskForm.url)

# === Ввод URL ===
@router.message(TaskForm.url)
async def process_url(message: Message, state: FSMContext):
    await state.update_data(url=message.text)
    await message.answer("Введите новое значение для поля <b>время повторения (минуты)</b>:", parse_mode="HTML")
    await state.set_state(TaskForm.time_repeat)

# === Ввод времени повторения ===
@router.message(TaskForm.time_repeat)
async def process_time_repeat(message: Message, state: FSMContext):
    try:
        time_repeat = int(message.text)
        await state.update_data(time_repeat=time_repeat)
        await message.answer("Введите новое значение для поля <b>количество страниц</b>:", parse_mode="HTML")
        await state.set_state(TaskForm.count_page)
    except ValueError:
        await message.answer("Неверный формат. Введите число:")

# === Ввод количества страниц ===
@router.message(TaskForm.count_page)
async def process_count_page(message: Message, state: FSMContext):
    try:
        count_page = int(message.text)
        await state.update_data(count_page=count_page)
        await message.answer("Введите новые ключевые слова через запятую <i>(можно оставить пустым)</i>:", parse_mode="HTML", reply_markup=skip_keyboard())
        await state.set_state(TaskForm.target_words)
    except ValueError:
        await message.answer("Неверный формат. Введите число:")

# === Ввод ключевых слов ===
@router.message(TaskForm.target_words)
async def process_target_words(message: Message, state: FSMContext):
    words = [w.strip() for w in message.text.split(",")] if message.text else []
    await state.update_data(target_words=words)
    await message.answer("Введите стоп-слова через запятую <i>(можно оставить пустым)</i>:", parse_mode="HTML", reply_markup=skip_keyboard())
    await state.set_state(TaskForm.stop_words)

# === Обработка нажатия "Пропустить" на шаге target_words ===
@router.callback_query(lambda call: call.data == "skip", TaskForm.target_words)
async def skip_target_words(call: CallbackQuery, state: FSMContext):
    await state.update_data(target_words=[])
    await call.message.edit_text("Введите стоп-слова через запятую <i>(можно оставить пустым)</i>:", parse_mode="HTML", reply_markup=skip_keyboard())
    await state.set_state(TaskForm.stop_words)

# === Ввод стоп-слов ===
@router.message(TaskForm.stop_words)
async def process_stop_words(message: Message, state: FSMContext):
    words = [w.strip() for w in message.text.split(",")] if message.text else []
    await state.update_data(stop_words=words)
    await message.answer("Введите лимит объявлений за цикл:")
    await state.set_state(TaskForm.max_ads_per_run)

# === Обработка нажатия "Пропустить" на шаге stop_words ===
@router.callback_query(lambda call: call.data == "skip", TaskForm.stop_words)
async def skip_stop_words(call: CallbackQuery, state: FSMContext):
    await state.update_data(stop_words=[])
    await call.message.edit_text("Введите лимит объявлений за цикл:")
    await state.set_state(TaskForm.max_ads_per_run)

# === Лимит объявлений ===
@router.message(TaskForm.max_ads_per_run)
async def process_max_ads(message: Message, state: FSMContext):
    try:
        max_ads = int(message.text)
        await state.update_data(max_ads_per_run=max_ads)
        await message.answer("Задача активна? (да/нет)")
        await state.set_state(TaskForm.activity)
    except ValueError:
        await message.answer("Неверный формат. Введите число:")

# === Активность задачи ===
@router.message(TaskForm.activity)
async def process_activity(message: Message, state: FSMContext):
    text = message.text.lower()
    activity = True if text in ["да", "yes", "1", "true"] else False
    await state.update_data(activity=activity)
    await message.answer("Отслеживать изменение цены? (да/нет)")
    await state.set_state(TaskForm.price_change)

# === Отслеживание цены ===
@router.message(TaskForm.price_change)
async def process_price_change(message: Message, state: FSMContext):
    text = message.text.lower()
    price_change = True if text in ["да", "yes", "1", "true"] else False
    await state.update_data(price_change=price_change)
    await message.answer("Отправлять все объявления? (да/нет)")
    await state.set_state(TaskForm.all_ads)

# === Сохранение задачи ===
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

# === Начало добавления задачи ===
@router.callback_query(lambda call: call.data == "add_task")
async def start_add_task(call: CallbackQuery, state: FSMContext):
    await state.set_state(TaskForm.number)
    await call.message.edit_text("Введите значение для поля <b>номер задачи</b>:", parse_mode="HTML")