from loader import load_tasks, load_page_config
from loguru import logger

from util.parser_avito import parse_avito

logger.add("parser.log", rotation="50 MB", level="INFO")


if __name__ == "__main__":
    tasks = load_tasks()
    page_config = load_page_config()

    for task in tasks:
        if task['activity']:
            parse_avito(task, page_config)