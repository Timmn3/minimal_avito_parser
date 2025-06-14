def format_task(task):
    return (
        f"📌 Задача #{task.number}\n"
        f"Метка: {task.teg}\n"
        f"URL: {task.url}\n"
        f"⏱ Интервал: {task.time_repeat} сек.\n"
        f"📄 Страниц: {task.count_page}\n"
        f"🎯 Ключевые слова: {', '.join(task.target_words)}\n"
        f"🚫 Стоп-слова: {', '.join(task.stop_words)}\n"
        f"🔢 Лимит объявлений: {task.max_ads_per_run}\n"
        f"✅ Активна: {'Да' if task.activity else 'Нет'}\n"
        # f"💰 Отслеживать изменения цены: {'Да' if task.price_change else 'Нет'}\n"
        # f"📢 Отправлять все объявления: {'Да' if task.all_ads else 'Нет'}"
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