from aiogram import Bot, types

async def set_default_commands(bot: Bot):
    commands = [
        types.BotCommand(command="start", description="Запустить бота"),
        types.BotCommand(command="menu", description="Меню"),
        types.BotCommand(command="tasks", description="Запуск задач"),
        types.BotCommand(command="help", description="Помощь"),
    ]

    await bot.set_my_commands(commands)