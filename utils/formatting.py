def format_task(task):
    return (
        f"📌 Задача #{task.number}\n"
        f"Метка: {task.teg}\n"
        f"URL: {task.url[:30]}...\n"
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
        "• <b>Мои задачи</b> — посмотреть и отредактировать активные ссылки\n"
        "• <b>Добавить задачу</b> — указать URL, метку и параметры парсинга\n"
        "• <b>Новые объявления</b> — посмотреть последние найденные товары\n"
        "• <b>Настройки</b> — изменить частоту проверки, фильтры слов и т.д.\n"
        "• <b>Помощь</b> — это окно с описанием"
    )