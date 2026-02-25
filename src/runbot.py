import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database.connection import create_pool, close_pool
from database.models import create_tables
from handlers import setup_routers
from scheduler.setup import setup_scheduler, start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


async def on_startup():
    await create_pool()
    await create_tables()
    setup_scheduler(bot)
    start_scheduler()
    logger.info("Bot started successfully")


async def on_shutdown():
    stop_scheduler()
    await close_pool()
    logger.info("Bot stopped")


async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    router = setup_routers()
    dp.include_router(router)

    logger.info("Starting bot polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")
