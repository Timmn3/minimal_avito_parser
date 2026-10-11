from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def setup_driver():
    options = Options()

    options.add_argument('--disable-blink-features=AutomationControlled')
    # Скрывает факт автоматизации, помогает обходить антибот-защиту

    # options.add_argument('--headless')
    # Запуск в фоновом режиме без графического интерфейса (актуально для серверов)

    options.add_argument('--no-sandbox')
    # Отключает песочницу Chrome, требуется для запуска в Docker или от root

    options.add_argument('--disable-dev-shm-usage')
    # Не использовать общую память /dev/shm, чтобы избежать ошибок в ограниченных средах

    options.add_argument('--disable-gpu')
    # Отключает GPU, т.к. в headless-режиме он не используется и может мешать

    options.add_argument('--memory-pressure-off')
    # Отключает уведомления о нехватке памяти, повышает стабильность при нагрузке

    options.page_load_strategy = 'none'

    # --- Дополнительные опции для минимального потребления ОЗУ --- #

    options.add_argument('--disable-software-rasterizer')
    # Отключает программный рендеринг, уменьшает нагрузку на процессор и память

    options.add_argument('--no-zygote')
    # Отключает вспомогательный процесс Chrome Zygote, уменьшает потребление памяти

    options.add_argument('--process-per-site')
    # Один процесс на сайт, ограничивает разрастание числа процессов

    options.add_argument('--media-cache-size=0')
    # Отключает кеш для медиа

    # Отключаем картинки и нотификации (ОЧЕНЬ важно!)
    prefs = {
        "profile.managed_default_content_settings.images": 2,  # Отключить загрузку картинок
        "profile.default_content_setting_values.notifications": 2,  # Отключить уведомления
        "profile.default_content_setting_values.automatic_downloads": 2,
    }

    options.add_experimental_option("prefs", prefs)

    # Отключаем фоновые таймеры, чтобы процессы не зависали в фоне
    options.add_argument('--disable-background-timer-throttling')  # Отключить ограничение таймеров в фоне
    options.add_argument('--disable-renderer-backgrounding')  # Отключить перевод рендереров в фоновый режим
    options.add_argument('--disable-backgrounding-occluded-windows')  # Отключить фоновую обработку окон вне экрана

    # Отключаем лишнюю защиту и IPC (иногда помогает уменьшить потребление ресурсов)
    options.add_argument('--disable-ipc-flooding-protection')  # Отключить защиту от "флуда" межпроцессными сообщениями

    # Отключаем обновления и ненужные сервисы
    options.add_argument('--disable-component-update')  # Отключить автообновление компонентов
    options.add_argument('--disable-sync')  # Отключить синхронизацию с Google

    # Минимизируем сбор метрик и краш-репортинг
    options.add_argument('--metrics-recording-only')  # Включить только сбор минимальных метрик
    options.add_argument('--disable-breakpad')  # Отключить сбор crash-дампов (breakpad)

    # Отключаем лишние встроенные сервисы безопасности
    options.add_argument('--disable-client-side-phishing-detection')  # Отключить антифишинговую защиту на клиенте
    options.add_argument('--disable-default-apps')  # Не загружать встроенные приложения Chrome

    return webdriver.Chrome(options=options)