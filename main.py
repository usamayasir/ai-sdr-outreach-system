"""Main entry point for the AI SDR system."""
import asyncio
from database.connection import engine
from database.models import Base
from bot.telegram_bot import TelegramControlCenter
from scheduler.jobs import JobScheduler


async def init_db():
    """Create all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[Main] Database initialized")


async def main():
    """Main entry point — start scheduler and Telegram bot."""
    await init_db()

    # Start background scheduler
    scheduler = JobScheduler()
    await scheduler.start()

    # Start Telegram bot
    bot = TelegramControlCenter()
    await bot.app.initialize()
    await bot.app.start()
    await bot.app.updater.start_polling()

    print("🤖 AI SDR System is running!")
    print("Use Telegram to control the system.")

    # Keep running
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
