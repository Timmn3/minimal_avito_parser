from aiogram import Bot, types

async def set_default_commands(bot: Bot):
    commands = [
        types.BotCommand(command="start", description="Запустить бота"),
        types.BotCommand(command="tasks", description="Показать все задачи"),
        types.BotCommand(command="my_tasks", description="Показать мои задачи"),
        types.BotCommand(command="add_task", description="Добавить новую задачу"),
        types.BotCommand(command="help", description="Показать помощь"),
        types.BotCommand(command="settings", description="Настройки уведомлений"),
    ]

    await bot.set_my_commands(commands)