def format_task(task):
    target_words = task.target_words or []
    stop_words = task.stop_words or []

    price_range = ""
    if task.min_price is not None or task.max_price is not None:
        min_p = f"{task.min_price:,}".replace(",", " ") if task.min_price is not None else "любая"
        max_p = f"{task.max_price:,}".replace(",", " ") if task.max_price is not None else "любая"
        price_range = f"💰 Диапазон цен: от {min_p} до {max_p} ₽\n"

    return (
        f"📌 Задача #{task.number}\n"
        f"Метка: {task.teg}\n"
        f"URL: {task.url}\n"
        f"⏱ Интервал: {task.time_repeat} сек.\n"
        f"{price_range}"
        f"🎯 Ключевые слова: {', '.join(target_words)}\n"
        f"🚫 Стоп-слова: {', '.join(stop_words)}\n"
        f"🔢 Лимит объявлений: {task.max_ads_per_run}\n"
        f"✅ Активна: {'Да' if task.activity else 'Нет'}\n"
    )

def format_ad(ad):
    return (
        f"📍#{ad['teg']}\n"
        f"{ad['title']}\n"
        f"{ad['price']}\n"
        f"{ad['link']}"
    )

def get_help_text():
    return (
        "❓ <b>Как пользоваться ботом:</b>\n\n"
        "• <b>Мои задачи</b> — посмотреть и отредактировать активные задачи\n"
        "• <b>Добавить задачу</b> — указать URL, метку и параметры парсинга\n\n"
        "По вопросам обращайтесь: https://t.me/bots_mm"
    )