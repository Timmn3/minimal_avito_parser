from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def setup_driver():
    options = Options()
    options.add_argument('--disable-blink-features=AutomationControlled')
    # options.add_argument('--headless')  # фоновый режим
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.page_load_strategy = 'none'
    return webdriver.Chrome(options=options)