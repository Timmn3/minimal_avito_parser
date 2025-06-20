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


def format_price(price: int) -> str:
    """Форматирует цену с разделителями тысяч (1 000)"""
    if price is None:
        return "не указана"
    return f"{price:,}".replace(",", " ") + " ₽"


# === Клавиатура для пропуска шага ===
def skip_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➡️ Пропустить", callback_data="skip")],
        [InlineKeyboardButton(text="✖️ Отменить", callback_data="main_menu")]
    ])


# === Получение следующего доступного номера задачи ===
async def get_next_task_number(user_id: int) -> int:
    async with async_session() as session:
        result = await session.execute(
            select(func.count(Task.id)).where(Task.user_id == user_id)
        )
        count = result.scalar()

        if count < 5:
            return count + 1
        return -1


# === Кнопка "Мои задачи" ===
@router.callback_query(lambda call: call.data == "my_tasks")
async def show_user_tasks(call: CallbackQuery):
    user_id = call.from_user.id
    async with async_session() as session:
        tasks = await get_user_tasks(session, user_id)
        sorted_tasks = sorted(tasks, key=lambda x: x.number)

    if not sorted_tasks:
        await call.message.edit_text("У вас нет задач.", reply_markup=get_back_button())
        await call.answer()
        return

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


@router.callback_query(lambda call: call.data.startswith("show_task_"))
async def show_single_task(call: CallbackQuery):
    task_id = int(call.data.split("_")[2])
    async with async_session() as session:
        result = await session.execute(select(Task).where(Task.id == task_id))
        task = result.scalars().first()

    if not task:
        await call.answer("Задача не найдена!")
        return

    await call.message.edit_text(
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

    reply_markup = skip_keyboard() if task.teg else get_cancel()
    await call.message.answer(
        f"Текущий номер задачи: {task.number}\nВведите <b>Имя задачи</b>:",
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
        result = await session.execute(
            select(Task).where(Task.id == task_id, Task.user_id == user_id)
        )
        task = result.scalars().first()

        if not task:
            await call.answer("Задача не найдена!", show_alert=True)
            return

        await session.execute(
            sa.delete(SeenAd).where(SeenAd.task_id == task_id)
        )
        await session.delete(task)
        await session.commit()

    await call.message.edit_text("🗑 Задача успешно удалена.", reply_markup=get_back_button())
    await call.answer()


# === Начало добавления задачи ===
@router.callback_query(lambda call: call.data == "add_task")
async def start_add_task(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id

    next_number = await get_next_task_number(user_id)
    if next_number == -1:
        await call.message.edit_text(
            "❌ Лимит задач исчерпан (максимум 5 задач).",
            reply_markup=get_back_button()
        )
        return

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
            f"Создана новая задача №{next_number}\nВведите <b>Имя задачи</b>:",
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
            current_data = {
                'url': task.url,
                'time_repeat': task.time_repeat,
                'count_page': task.count_page,
                'target_words': task.target_words,
                'stop_words': task.stop_words,
                'max_ads_per_run': task.max_ads_per_run,
                'min_price': task.min_price,
                'max_price': task.max_price
            }
            await state.update_data(**current_data)
            reply_markup = skip_keyboard()
        else:
            reply_markup = get_cancel()

    await message.answer(
        "Введите <b>ссылку URL из браузера</b>:",
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    await state.set_state(TaskForm.url)


@router.callback_query(lambda call: call.data == "skip", TaskForm.teg)
async def skip_teg(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    task_id = data.get("task_id")

    async with async_session() as session:
        result = await session.execute(select(Task).where(Task.id == task_id))
        task = result.scalars().first()
        if task is not None:
            await state.update_data(teg=task.teg)
            current_data = {
                'url': task.url,
                'time_repeat': task.time_repeat,
                'count_page': task.count_page,
                'target_words': task.target_words,
                'stop_words': task.stop_words,
                'max_ads_per_run': task.max_ads_per_run,
                'min_price': task.min_price,
                'max_price': task.max_price
            }
            await state.update_data(**current_data)
            reply_markup = skip_keyboard()
        else:
            reply_markup = get_cancel()

    await call.message.edit_text(
        "Введите <b>ссылку URL из браузера</b>:",
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    await state.set_state(TaskForm.url)


# === Ввод URL ===
@router.message(TaskForm.url)
async def process_url(message: Message, state: FSMContext):
    await state.update_data(url=message.text)

    await message.answer(
        "Введите <b>интервал запросов на сайт (секунды)</b>:",
        parse_mode="HTML",
        reply_markup=skip_keyboard()
    )
    await state.set_state(TaskForm.time_repeat)


@router.callback_query(lambda call: call.data == "skip", TaskForm.url)
async def skip_url(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    task_id = data.get("task_id")

    async with async_session() as session:
        result = await session.execute(select(Task).where(Task.id == task_id))
        task = result.scalars().first()
        await state.update_data(url=task.url)

    await call.message.edit_text(
        "Введите <b>интервал запросов на сайт (секунды)</b>:",
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

        await state.update_data(count_page=1)

        await message.answer(
            "Введите <b>ключевые слова</b> через запятую (например: квартира, балкон):",
            parse_mode="HTML",
            reply_markup=skip_keyboard()
        )
        await state.set_state(TaskForm.target_words)

    except ValueError:
        await message.answer("Неверный формат. Введите число:", reply_markup=get_cancel())

# === Обработчик пропуска для time_repeat ===
@router.callback_query(lambda call: call.data == "skip", TaskForm.time_repeat)
async def skip_time_repeat(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    task_id = data.get("task_id")

    async with async_session() as session:
        result = await session.execute(select(Task).where(Task.id == task_id))
        task = result.scalars().first()

        if task is not None:
            time_repeat = task.time_repeat
        else:
            time_repeat = 30  # Значение по умолчанию

        await state.update_data(time_repeat=time_repeat)
        await state.update_data(count_page=1)

    await call.message.edit_text(
        "Введите <b>ключевые слова</b> через запятую (например: квартира, балкон):",
        parse_mode="HTML",
        reply_markup=skip_keyboard()
    )
    await state.set_state(TaskForm.target_words)

# === Ввод ключевых слов ===
@router.message(TaskForm.target_words)
async def process_target_words(message: Message, state: FSMContext):
    words = [w.strip() for w in message.text.split(",")] if message.text else []
    await state.update_data(target_words=words)
    await message.answer(
        "Введите стоп-слова через запятую <i>(можно оставить пустым)</i>:",
        parse_mode="HTML",
        reply_markup=skip_keyboard()
    )
    await state.set_state(TaskForm.stop_words)


@router.callback_query(lambda call: call.data == "skip", TaskForm.target_words)
async def skip_target_words(call: CallbackQuery, state: FSMContext):
    await state.update_data(target_words=[])
    await call.message.edit_text(
        "Введите стоп-слова через запятую <i>(можно оставить пустым)</i>:",
        parse_mode="HTML",
        reply_markup=skip_keyboard()
    )
    await state.set_state(TaskForm.stop_words)


# === Ввод стоп-слов ===
@router.message(TaskForm.stop_words)
async def process_stop_words(message: Message, state: FSMContext):
    words = [w.strip() for w in message.text.split(",")] if message.text else []
    await state.update_data(stop_words=words)
    await message.answer(
        "Введите минимальную цену в рублях (только число, без пробелов)\n"
        "Или нажмите 'Пропустить', если не хотите указывать:",
        reply_markup=skip_keyboard()
    )
    await state.set_state(TaskForm.min_price)


@router.callback_query(lambda call: call.data == "skip", TaskForm.stop_words)
async def skip_stop_words(call: CallbackQuery, state: FSMContext):
    await state.update_data(stop_words=[])
    await call.message.edit_text(
        "Введите минимальную цену в рублях (только число, без пробелов)\n"
        "Или нажмите 'Пропустить', если не хотите указывать:",
        reply_markup=skip_keyboard()
    )
    await state.set_state(TaskForm.min_price)


# === Ввод минимальной цены ===
@router.message(TaskForm.min_price)
async def process_min_price(message: Message, state: FSMContext):
    if message.text and message.text.isdigit():
        min_price = int(message.text)
        if min_price < 0:
            await message.answer("Цена не может быть отрицательной. Введите снова:")
            return

        await state.update_data(min_price=min_price)
        await message.answer(
            "Введите максимальную цену в рублях (только число, без пробелов)\n"
            "Или нажмите 'Пропустить', если не хотите указывать:",
            reply_markup=skip_keyboard()
        )
        await state.set_state(TaskForm.max_price)
    else:
        await message.answer(
            "Пожалуйста, введите число (например: 50000) или нажмите 'Пропустить'",
            reply_markup=skip_keyboard()
        )


@router.callback_query(lambda call: call.data == "skip", TaskForm.min_price)
async def skip_min_price(call: CallbackQuery, state: FSMContext):
    await state.update_data(min_price=None)
    await call.message.edit_text(
        "Введите максимальную цену в рублях (только число, без пробелов)\n"
        "Или нажмите 'Пропустить', если не хотите указывать:",
        reply_markup=skip_keyboard()
    )
    await state.set_state(TaskForm.max_price)


# === Ввод максимальной цены ===
@router.message(TaskForm.max_price)
async def process_max_price(message: Message, state: FSMContext):
    if message.text and message.text.isdigit():
        max_price = int(message.text)
        if max_price < 0:
            await message.answer("Цена не может быть отрицательной. Введите снова:")
            return

        data = await state.get_data()

        if data.get('min_price') and max_price < data['min_price']:
            await message.answer(
                "Максимальная цена должна быть больше минимальной. Введите снова:",
                reply_markup=skip_keyboard()
            )
            return

        await state.update_data(max_price=max_price)
        await message.answer(
            "Введите лимит объявлений за цикл (максимум 50):",
            reply_markup=skip_keyboard()
        )
        await state.set_state(TaskForm.max_ads_per_run)
    else:
        await message.answer(
            "Пожалуйста, введите число (например: 100000) или нажмите 'Пропустить'",
            reply_markup=skip_keyboard()
        )


@router.callback_query(lambda call: call.data == "skip", TaskForm.max_price)
async def skip_max_price(call: CallbackQuery, state: FSMContext):
    await state.update_data(max_price=None)
    data = await state.get_data()
    await state.update_data(max_ads_per_run=10)

    update_data = {
        'activity': data.get('activity', False),
        'price_change': data.get('price_change', False),
        'all_ads': data.get('all_ads', False),
        'max_ads_per_run': 10,
        'min_price': None,
        'max_price': None
    }

    async with async_session() as session:
        await update_task(session, data['task_id'], {**data, **update_data})

    await call.message.edit_text("✅ Задача успешно обновлена!", reply_markup=run_task(data['task_id']))
    await state.clear()


# === Лимит объявлений ===
@router.message(TaskForm.max_ads_per_run)
async def process_max_ads(message: Message, state: FSMContext):
    try:
        max_ads = int(message.text)
        if max_ads > 50:
            await message.answer("Максимальное значение — 50. Введите снова:")
            return
        if max_ads <= 0:
            await message.answer("Значение должно быть больше 0. Введите снова:")
            return

        data = await state.get_data()
        update_data = {
            'activity': data.get('activity', False),
            'price_change': data.get('price_change', False),
            'all_ads': data.get('all_ads', False),
            'max_ads_per_run': max_ads,
            'min_price': data.get('min_price'),
            'max_price': data.get('max_price')
        }

        task_id = data.get("task_id")
        async with async_session() as session:
            await update_task(session, task_id, {**data, **update_data})

        await message.answer("✅ Задача успешно обновлена!", reply_markup=run_task(task_id))
        await state.clear()
    except ValueError:
        await message.answer("Неверный формат. Введите число:", reply_markup=get_cancel())


@router.callback_query(lambda call: call.data == "skip", TaskForm.max_ads_per_run)
async def skip_max_ads(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    task_id = data.get("task_id")

    async with async_session() as session:
        result = await session.execute(select(Task).where(Task.id == task_id))
        task = result.scalars().first()

        max_ads_per_run = task.max_ads_per_run if task else 50

        update_data = {
            'activity': data.get('activity', False),
            'price_change': data.get('price_change', False),
            'all_ads': data.get('all_ads', False),
            'max_ads_per_run': max_ads_per_run,
            'min_price': data.get('min_price'),
            'max_price': data.get('max_price')
        }
        await update_task(session, task_id, {**data, **update_data})

    await call.message.edit_text("✅ Задача успешно обновлена!", reply_markup=run_task(task_id))
    await state.clear()


async def build_tasks_keyboard(user_id: int) -> tuple[InlineKeyboardMarkup, bool]:
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

        new_status = not task.activity
        task.activity = new_status
        await session.commit()

        status_text = "включена" if new_status else "выключена"
        await call.answer(f"Задача {task.teg} {status_text}", show_alert=False)

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
    await call.message.edit_reply_markup(reply_markup=None)