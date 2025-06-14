from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, func
import sqlalchemy as sa
from database.models import Task, SeenAd
from states.task_states import TaskForm
from keyboards.inline import get_task_actions_keyboard, get_back_button, get_cancel, run_task
from utils.formatting import format_task
from database.db import async_session, get_user_tasks, update_task

router = Router()


# === Клавиатура для пропуска шага ===
def skip_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➡️ Пропустить", callback_data="skip")]
    ,
    [InlineKeyboardButton(text="✖️ Отменить", callback_data="main_menu")]])


# === Получение следующего доступного номера задачи ===
async def get_next_task_number(user_id: int) -> int:
    async with async_session() as session:
        # Получаем текущее количество задач пользователя
        result = await session.execute(
            select(func.count(Task.id)).where(Task.user_id == user_id)
        )
        count = result.scalar()

        # Если задач меньше 5, возвращаем следующий номер
        if count < 5:
            return count + 1
        return -1  # -1 означает, что лимит исчерпан


# === Кнопка "Мои задачи" ===
@router.callback_query(lambda call: call.data == "my_tasks")
async def show_user_tasks(call: CallbackQuery):
    user_id = call.from_user.id
    async with async_session() as session:
        tasks = await get_user_tasks(session, user_id)
        sorted_tasks = sorted(tasks, key=lambda x: x.number)  # <-- сортировка

    if not sorted_tasks:
        await call.message.edit_text("У вас нет задач.", reply_markup=get_back_button())
        await call.answer()
        return

    # Создаем клавиатуру с кнопками задач
    builder = InlineKeyboardBuilder()
    for task in sorted_tasks:
        builder.row(
            InlineKeyboardButton(
                text=f"Задача #{task.number}: {task.teg}",
                callback_data=f"show_task_{task.id}"
            )
        )
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu"))

    await call.message.edit_text(
        "Ваши задачи:",
        reply_markup=builder.as_markup()
    )
    await call.answer()



# Добавьте новый обработчик для показа конкретной задачи
@router.callback_query(lambda call: call.data.startswith("show_task_"))
async def show_single_task(call: CallbackQuery):
    task_id = int(call.data.split("_")[2])
    async with async_session() as session:
        result = await session.execute(select(Task).where(Task.id == task_id))
        task = result.scalars().first()

    if not task:
        await call.answer("Задача не найдена!")
        return

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
            await call.message.edit_text(
                "❌ Лимит задач исчерпан (максимум 5 задач).",
                reply_markup=get_back_button()
            )
            return

    await state.update_data(task_id=task_id, user_id=user_id, number=task.number)

    # Проверяем, есть ли уже значение teg в БД
    reply_markup = skip_keyboard() if task.teg else get_cancel()
    await call.message.answer(
        f"Текущий номер задачи: {task.number}\nВведите новое значение для поля <b>метка задачи (teg)</b>:",
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    await call.answer()
    await state.set_state(TaskForm.teg)


@router.callback_query(lambda call: call.data.startswith("delete_task_"))
async def delete_task_handler(call: CallbackQuery):
    task_id = int(call.data.split("_")[2])
    user_id = call.from_user.id

    async with async_session() as session:
        # Проверяем, что задача принадлежит пользователю
        result = await session.execute(
            select(Task).where(Task.id == task_id, Task.user_id == user_id)
        )
        task = result.scalars().first()

        if not task:
            await call.answer("Задача не найдена!", show_alert=True)
            return

        # Удаляем связанные объявления
        await session.execute(
            sa.delete(SeenAd).where(SeenAd.task_id == task_id)
        )

        # Удаляем задачу
        await session.delete(task)
        await session.commit()

    await call.message.edit_text("🗑 Задача успешно удалена.", reply_markup=get_back_button())
    await call.answer()


# === Начало добавления задачи ===
@router.callback_query(lambda call: call.data == "add_task")
async def start_add_task(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id

    # Проверяем лимит задач
    next_number = await get_next_task_number(user_id)
    if next_number == -1:
        await call.message.edit_text(
            "❌ Лимит задач исчерпан (максимум 5 задач).",
            reply_markup=get_back_button()
        )
        return

    # Создаем новую задачу с автоматическим номером
    async with async_session() as session:
        new_task = Task(user_id=user_id, number=next_number)
        session.add(new_task)
        await session.flush()
        await session.refresh(new_task)

        await state.update_data(
            task_id=new_task.id,
            user_id=user_id,
            number=next_number
        )

        await call.message.edit_text(
            f"Создана новая задача №{next_number}\nВведите значение для поля <b>метка задачи (teg)</b>:",
            parse_mode="HTML",
            reply_markup=get_cancel()
        )
        await state.set_state(TaskForm.teg)


# === Ввод метки задачи ===
@router.message(TaskForm.teg)
async def process_teg(message: Message, state: FSMContext):
    await state.update_data(teg=message.text)
    data = await state.get_data()
    task_id = data.get("task_id")

    async with async_session() as session:
        result = await session.execute(select(Task).where(Task.id == task_id))
        task = result.scalars().first()
        if task is not None:
            # Загружаем текущие данные из БД в состояние
            current_data = {
                'url': task.url,
                'time_repeat': task.time_repeat,
                'count_page': task.count_page,
                'target_words': task.target_words,
                'stop_words': task.stop_words,
                'max_ads_per_run': task.max_ads_per_run
            }
            await state.update_data(**current_data)

            reply_markup = skip_keyboard()
        else:
            reply_markup = get_cancel()

    await message.answer(
        "Введите новое значение для поля <b>URL</b>:",
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    await state.set_state(TaskForm.url)


# Обработчик пропуска для teg
@router.callback_query(lambda call: call.data == "skip", TaskForm.teg)
async def skip_teg(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    task_id = data.get("task_id")

    async with async_session() as session:
        result = await session.execute(select(Task).where(Task.id == task_id))
        task = result.scalars().first()
        if task is not None:
            # Сохраняем текущее значение teg из БД
            await state.update_data(teg=task.teg)
            # Загружаем остальные данные из БД
            current_data = {
                'url': task.url,
                'time_repeat': task.time_repeat,
                'count_page': task.count_page,
                'target_words': task.target_words,
                'stop_words': task.stop_words,
                'max_ads_per_run': task.max_ads_per_run
            }
            await state.update_data(**current_data)
            reply_markup = skip_keyboard()
        else:
            reply_markup = get_cancel()

    await call.message.edit_text(
        "Введите новое значение для поля <b>URL</b>:",
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    await state.set_state(TaskForm.url)


# === Ввод URL ===
@router.message(TaskForm.url)
async def process_url(message: Message, state: FSMContext):
    await state.update_data(url=message.text)

    await message.answer(
        "Введите новое значение для поля <b>время повторения (секунды)</b>:",
        parse_mode="HTML",
        reply_markup=skip_keyboard()  # Всегда показываем кнопку пропуска для числовых полей
    )
    await state.set_state(TaskForm.time_repeat)


# Обработчик пропуска для url
@router.callback_query(lambda call: call.data == "skip", TaskForm.url)
async def skip_url(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    task_id = data.get("task_id")

    async with async_session() as session:
        result = await session.execute(select(Task).where(Task.id == task_id))
        task = result.scalars().first()
        # Сохраняем текущее значение url из БД
        await state.update_data(url=task.url)

    await call.message.edit_text(
        "Введите новое значение для поля <b>время повторения (секунды)</b>:",
        parse_mode="HTML",
        reply_markup=skip_keyboard()
    )
    await state.set_state(TaskForm.time_repeat)


# === Ввод времени повторения ===
@router.message(TaskForm.time_repeat)
async def process_time_repeat(message: Message, state: FSMContext):
    try:
        time_repeat = int(message.text)
        if time_repeat < 5:
            await message.answer("Минимальное значение — 5 секунд. Введите снова:")
            return
        await state.update_data(time_repeat=time_repeat)

        # Устанавливаем count_page = 1 по умолчанию
        await state.update_data(count_page=1)

        await message.answer(
            "Введите лимит количества объявлений за цикл (максимум 50):",
            parse_mode="HTML",
            reply_markup=skip_keyboard()
        )
        await state.set_state(TaskForm.max_ads_per_run)
    except ValueError:
        await message.answer("Неверный формат. Введите число:", reply_markup=get_cancel())



# Обработчик пропуска для time_repeat
@router.callback_query(lambda call: call.data == "skip", TaskForm.time_repeat)
async def skip_time_repeat(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    task_id = data.get("task_id")

    async with async_session() as session:
        result = await session.execute(select(Task).where(Task.id == task_id))
        task = result.scalars().first()
        # Сохраняем текущее значение time_repeat из БД
        await state.update_data(time_repeat=task.time_repeat)

    await call.message.edit_text(
        "Введите новое значение для поля <b>количество страниц</b>:",
        parse_mode="HTML",
        reply_markup=skip_keyboard()
    )
    await state.set_state(TaskForm.count_page)


# === Лимит объявлений ===
@router.message(TaskForm.max_ads_per_run)
async def process_max_ads(message: Message, state: FSMContext):
    try:
        max_ads = int(message.text)
        if max_ads > 50:
            await message.answer("Максимальное значение — 50. Введите снова:")
            return

        await state.update_data(max_ads_per_run=max_ads)

        # Устанавливаем значения по умолчанию для пропущенных полей
        data = await state.get_data()
        update_data = {
            'activity': data.get('activity', False),
            'price_change': data.get('price_change', False),
            'all_ads': data.get('all_ads', False),
            'max_ads_per_run': max_ads
        }

        # Обновляем задачу в БД
        task_id = data.get("task_id")
        async with async_session() as session:
            await update_task(session, task_id, {**data, **update_data})

        await message.answer("✅ Задача успешно обновлена!", reply_markup=run_task(task_id))
        await state.clear()
    except ValueError:
        await message.answer("Неверный формат. Введите число:", reply_markup=get_cancel())



# Обработчик пропуска для max_ads_per_run
@router.callback_query(lambda call: call.data == "skip", TaskForm.max_ads_per_run)
async def skip_max_ads(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    task_id = data.get("task_id")

    async with async_session() as session:
        result = await session.execute(select(Task).where(Task.id == task_id))
        task = result.scalars().first()
        # Сохраняем текущее значение max_ads_per_run из БД
        await state.update_data(max_ads_per_run=task.max_ads_per_run)

        # Обновляем задачу в БД
        update_data = {
            'activity': data.get('activity', False),
            'price_change': data.get('price_change', False),
            'all_ads': data.get('all_ads', False),
            'max_ads_per_run': task.max_ads_per_run
        }
        await update_task(session, task_id, {**data, **update_data})

    await call.message.edit_text("✅ Задача успешно обновлена!", reply_markup=run_task(task_id))
    await state.clear()


async def build_tasks_keyboard(user_id: int) -> tuple[InlineKeyboardMarkup, bool]:
    """
    Создает клавиатуру с задачами пользователя.
    Возвращает кортеж (клавиатура, есть_ли_задачи)
    """
    async with async_session() as session:
        tasks = await get_user_tasks(session, user_id)
        sorted_tasks = sorted(tasks, key=lambda x: x.number)

    if not sorted_tasks:
        return None, False

    builder = InlineKeyboardBuilder()
    for task in sorted_tasks:
        status = "✅" if task.activity else "❌"
        builder.row(
            InlineKeyboardButton(
                text=f"#{task.number} {task.teg} {status}",
                callback_data=f"toggle_task_{task.id}"
            )
        )
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu"))

    return builder.as_markup(), True


@router.message(Command("tasks"))
@router.message(lambda msg: msg.text == "Запуск задач")
async def manage_tasks_activity(message: Message):
    keyboard, has_tasks = await build_tasks_keyboard(message.from_user.id)

    if not has_tasks:
        await message.answer("У вас нет задач.", reply_markup=get_back_button())
        return

    await message.answer(
        "Управление активностью задач:",
        reply_markup=keyboard
    )


@router.callback_query(lambda call: call.data.startswith("toggle_task_"))
async def toggle_task_activity(call: CallbackQuery):
    task_id = int(call.data.split("_")[2])
    user_id = call.from_user.id

    async with async_session() as session:
        result = await session.execute(
            select(Task).where(Task.id == task_id, Task.user_id == user_id)
        )
        task = result.scalars().first()

        if not task:
            await call.answer("Задача не найдена!", show_alert=True)
            return

        # Меняем состояние активности
        new_status = not task.activity
        task.activity = new_status
        await session.commit()

        # Формируем текст для всплывающего уведомления
        status_text = "включена" if new_status else "выключена"
        notification_text = f"Задача {task.teg} {status_text}"

        # Отправляем всплывающее уведомление (исчезнет автоматически через 1.5 сек)
        await call.answer(notification_text, show_alert=False)

        # Обновляем клавиатуру
        keyboard, _ = await build_tasks_keyboard(user_id)
        await call.message.edit_reply_markup(reply_markup=keyboard)


@router.callback_query(lambda call: call.data.startswith("run_task_"))
async def handle_run_task(call: CallbackQuery):
    task_id = int(call.data.split("_")[2])
    user_id = call.from_user.id

    async with async_session() as session:
        result = await session.execute(select(Task).where(Task.id == task_id, Task.user_id == user_id))
        task = result.scalars().first()

        if not task:
            await call.answer("Задача не найдена!", show_alert=True)
            return

        task.activity = True
        await session.commit()

    await call.answer("✅ Задача активирована!", show_alert=False)
    await call.message.edit_reply_markup(reply_markup=None)  # убираем кнопку после нажатия


