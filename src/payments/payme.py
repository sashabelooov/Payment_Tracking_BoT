"""
Payme payment integration via Telegram Payments API.

Uses the provider token obtained from @BotFather → Settings → Payments → Payme.
Test mode token from @PaymeBusinessTest, live mode from @PaymeBusiness.
"""

from aiogram import Bot
from aiogram.types import LabeledPrice

from config import PAYME_PROVIDER_TOKEN, MONTHLY_PAYMENT


async def send_payme_invoice(bot: Bot, chat_id: int, billing_period: int, lang: str):
    """Send a Telegram payment invoice using Payme provider."""
    if lang == "🇺🇿 uz":
        title = "Buxgalteriya kursi to'lovi"
        description = f"Kurs uchun {billing_period}-to'lov (1 000 000 so'm)"
    else:
        title = "Оплата курса бухгалтерии"
        description = f"Оплата курса, период {billing_period} (1 000 000 сум)"

    prices = [
        LabeledPrice(label=title, amount=MONTHLY_PAYMENT * 100),  # amount in tiyin
    ]

    await bot.send_invoice(
        chat_id=chat_id,
        title=title,
        description=description,
        payload=f"payme_{chat_id}_{billing_period}",
        provider_token=PAYME_PROVIDER_TOKEN,
        currency="UZS",
        prices=prices,
        start_parameter=f"payment_{billing_period}",
    )


async def send_payme_invoice_for_course(bot: Bot, chat_id: int, course: dict,
                                         billing_period: int, lang: str):
    """Send a Telegram payment invoice for a specific course using Payme."""
    title = course['title']
    monthly = course['monthly_amount']
    if lang == "🇺🇿 uz":
        description = f"{title} uchun {billing_period}-to'lov ({monthly:,} so'm)"
    else:
        description = f"Оплата за {title}, период {billing_period} ({monthly:,} сум)"

    prices = [LabeledPrice(label=title, amount=monthly * 100)]

    await bot.send_invoice(
        chat_id=chat_id,
        title=title,
        description=description,
        payload=f"payme_{chat_id}_c{course['id']}_{billing_period}",
        provider_token=PAYME_PROVIDER_TOKEN,
        currency="UZS",
        prices=prices,
        start_parameter=f"course_{course['id']}_{billing_period}",
    )
