import asyncio
import logging
import asyncpg
from aiogram import Bot, Dispatcher, F
from aiogram.types import CallbackQuery
from aiogram.fsm.storage.memory import MemoryStorage

from app.config.config import Config, load_config
from app.handlers.onboarding import onboarding_router
from app.handlers.deposit import deposit_router
from app.handlers.create_task import create_task_router
from app.handlers.execute_task import execute_task_router
from app.keyboards.onboarding import get_main_menu_keyboard
from app.scheduler import setup_scheduler

logger = logging.getLogger(__name__)

# Универсальный обработчик для возврата в главное меню
async def back_to_main_menu(callback: CallbackQuery):
    await callback.message.edit_text("Главное меню:", reply_markup=get_main_menu_keyboard())

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s',
    )
    logger.info("Starting bot")

    config: Config = load_config(".env")

    pool = await asyncpg.create_pool(
        user=config.db.user, password=config.db.password,
        database=config.db.name, host=config.db.host,
        port=config.db.port
    )

    storage = MemoryStorage()

    bot = Bot(token=config.tg_bot.token, parse_mode="HTML")
    dp = Dispatcher(storage=storage, pool=pool, config=config)

    # Настраиваем и запускаем планировщик
    scheduler = setup_scheduler(bot, pool)
    scheduler.start()

    # Регистрируем "глобальный" обработчик для кнопки "Назад"
    dp.callback_query.register(back_to_main_menu, F.data == "main_menu")

    # Register handlers
    dp.include_router(onboarding_router)
    dp.include_router(deposit_router)
    dp.include_router(create_task_router)
    dp.include_router(execute_task_router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.error("Bot stopped!")
