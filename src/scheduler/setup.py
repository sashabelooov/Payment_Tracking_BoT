import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot

from config import BILLING_CHECK_HOUR
from scheduler.tasks import send_reminders, check_and_remove_expired

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def setup_scheduler(bot: Bot):
    """Configure and register all scheduled jobs."""

    # Send reminders daily at 9:00 AM
    scheduler.add_job(
        send_reminders,
        trigger=CronTrigger(hour=BILLING_CHECK_HOUR, minute=0),
        args=[bot],
        id="send_reminders",
        replace_existing=True,
    )

    # Check and remove expired users daily at 10:00 AM
    scheduler.add_job(
        check_and_remove_expired,
        trigger=CronTrigger(hour=BILLING_CHECK_HOUR + 1, minute=0),
        args=[bot],
        id="check_expired",
        replace_existing=True,
    )

    logger.info("Scheduler configured with daily billing checks")


def start_scheduler():
    scheduler.start()
    logger.info("Scheduler started")


def stop_scheduler():
    scheduler.shutdown()
    logger.info("Scheduler stopped")
