import json
import os

PATH = './data/'  # текущая директория
USER_AGENT_FILE = os.path.join(PATH, 'user-agent-database.txt')
TASKS_FILE = os.path.join(PATH, 'setting_tasks.txt')
PAGE_CONFIG_FILE = os.path.join(PATH, 'page_configuration.txt')

def load_tasks():
    with open(TASKS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [data[f"task{i}"][0] for i in range(1, 9) if f"task{i}" in data]


def load_page_config():
    with open(PAGE_CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

