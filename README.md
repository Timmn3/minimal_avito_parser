# minimal avito parser

Минимальный парсер Avito: базовая версия без лишних зависимостей

## Стек

- **Python 3**
- `selenium~` · `beautifulsoup4~` · `loguru~` · `asyncio~` · `aiogram~` · `sqlalchemy~` · `dotenv~` · `python-dotenv~` · `alembic~` · `psycopg2-binary~` · `asyncpg~` · `apscheduler`

## Структура

```text
LICENSE
alembic
alembic.ini
config.py
database
handlers
keyboards
main.py
middlewares
parsing
requirements.txt
services
states
utils
```

## Установка

```bash
git clone https://github.com/Timmn3/minimal_avito_parser.git
cd minimal_avito_parser
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scriptsctivate
pip install -r requirements.txt
```

## Запуск

```bash
python3 main.py
```

## Лицензия

MIT
