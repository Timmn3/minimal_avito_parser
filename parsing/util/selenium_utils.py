from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def setup_driver():
    options = Options()

    options.add_argument('--disable-blink-features=AutomationControlled')
    # Скрывает факт автоматизации, помогает обходить антибот-защиту

    options.add_argument('--headless')
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
    return webdriver.Chrome(options=options)