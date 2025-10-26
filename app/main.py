import asyncio
import logging
import asyncpg
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config.config import Config, load_config
from app.handlers.onboarding import onboarding_router

logger = logging.getLogger(__name__)

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s',
    )
    logger.info("Starting bot")

    config: Config = load_config(".env")

    # Создаем пул соединений с БД
    pool = await asyncpg.create_pool(
        user=config.db.user, password=config.db.password,
        database=config.db.name, host=config.db.host,
        port=config.db.port
    )

    storage = MemoryStorage()

    bot = Bot(token=config.tg_bot.token, parse_mode="HTML")
    # Передаем пул соединений в Dispatcher
    dp = Dispatcher(storage=storage, pool=pool)

    # Register handlers
    dp.include_router(onboarding_router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.error("Bot stopped!")
