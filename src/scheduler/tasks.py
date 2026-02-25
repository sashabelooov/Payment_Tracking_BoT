import json
import logging
from aiogram import Bot

from config import GROUP_ID, REMINDER_DAYS
from database.queries import (
    get_users_with_upcoming_billing,
    get_users_with_expired_billing,
    deactivate_user,
)

logger = logging.getLogger(__name__)

with open("data.json", "r", encoding="utf-8") as file:
    translations = json.load(file)


def get_text(lang, category, key):
    return translations.get(lang, {}).get(category, {}).get(key, f"[{key}]")


async def send_reminders(bot: Bot):
    """Send payment reminders to users whose billing is due in REMINDER_DAYS days."""
    for days in REMINDER_DAYS:
        users = await get_users_with_upcoming_billing(days)
        for user in users:
            lang = user['language']
            text = get_text(lang, 'message_text', 'payment_reminder').format(
                date=user['next_billing_date'].strftime('%d.%m.%Y'),
            )
            try:
                await bot.send_message(chat_id=user['telegram_id'], text=text)
                logger.info(f"Reminder sent to {user['telegram_id']} ({days} days before)")
            except Exception as e:
                logger.error(f"Failed to send reminder to {user['telegram_id']}: {e}")


async def check_and_remove_expired(bot: Bot):
    """Check for expired billings and remove users from the group."""
    if not GROUP_ID:
        logger.warning("GROUP_ID not configured, skipping expired billing check")
        return

    expired_users = await get_users_with_expired_billing()
    for user in expired_users:
        lang = user['language']
        try:
            await bot.ban_chat_member(chat_id=GROUP_ID, user_id=user['telegram_id'])
            await bot.unban_chat_member(chat_id=GROUP_ID, user_id=user['telegram_id'])
            logger.info(f"Removed {user['telegram_id']} from group (billing expired)")
        except Exception as e:
            logger.error(f"Failed to remove {user['telegram_id']} from group: {e}")

        await deactivate_user(user['telegram_id'])

        try:
            text = get_text(lang, 'message_text', 'payment_overdue')
            await bot.send_message(chat_id=user['telegram_id'], text=text)
        except Exception as e:
            logger.error(f"Failed to notify {user['telegram_id']}: {e}")
