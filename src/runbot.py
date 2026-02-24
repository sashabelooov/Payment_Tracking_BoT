import asyncio
import logging

from core.main import router,dp,bot


logging.basicConfig(level=logging.INFO)

async def main():
    logging.info("🤖 The bot is running........................................")
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("The Bot is stopped")