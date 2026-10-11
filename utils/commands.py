from aiogram import Bot, types
from loguru import logger

from config import ADMIN_IDS


async def set_default_commands(bot: Bot):
    commands = [
        types.BotCommand(command="start", description="Запустить бота"),
        types.BotCommand(command="menu", description="Меню"),
        types.BotCommand(command="tasks", description="Запуск задач"),
        types.BotCommand(command="help", description="Помощь"),
    ]

    await bot.set_my_commands(commands)

    # /settings виден только админам: у них свой список команд в личном чате
    admin_commands = commands + [types.BotCommand(command="settings", description="Настройки")]
    for admin_id in ADMIN_IDS:
        try:
            await bot.set_my_commands(admin_commands, scope=types.BotCommandScopeChat(chat_id=admin_id))
        except Exception as e:
            logger.warning(f"Не удалось задать команды админу {admin_id} (он ещё не писал боту?): {e}")
