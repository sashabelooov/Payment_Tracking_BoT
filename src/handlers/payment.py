import json
from datetime import date, timedelta

from aiogram import Router, Bot, F
from aiogram.types import Message, PreCheckoutQuery
from aiogram.fsm.context import FSMContext

from states import UserState
import keyboards as kb
from config import GROUP_ID, MONTHLY_PAYMENT, MONTHS_COUNT
from database.queries import (
    get_user, get_last_payment, create_payment,
    update_user_billing, get_course,
    get_user_enrollment_by_telegram, enroll_user,
    update_enrollment_billing, create_payment_for_course,
)
from payments.click import send_click_invoice
from payments.payme import send_payme_invoice

router = Router()

with open("data.json", "r", encoding="utf-8") as file:
    translations = json.load(file)


def get_text(lang, category, key):
    return translations.get(lang, {}).get(category, {}).get(key, f"[{key}]")


# --- Payment menu ---

@router.message(UserState.payment_menu)
async def payment_menu_handler(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    lang = data.get('language', '🇺🇿 uz')

    make_payment_btn = get_text(lang, 'buttons', 'make_payment')
    last_billing_btn = get_text(lang, 'buttons', 'last_billing')
    back_btn = get_text(lang, 'buttons', 'back')

    if message.text == make_payment_btn:
        user = await get_user(message.from_user.id)
        if user and user['payments_completed'] >= MONTHS_COUNT:
            await message.answer(
                text=get_text(lang, 'message_text', 'all_payments_done'),
                reply_markup=kb.payment_menu(lang),
            )
            return
        await message.answer(
            text=get_text(lang, 'message_text', 'make_payment_text'),
            reply_markup=kb.payment_method_menu(lang),
        )
        await state.set_state(UserState.payment_method)

    elif message.text == last_billing_btn:
        last = await get_last_payment(message.from_user.id)
        if last:
            text = get_text(lang, 'message_text', 'last_payment_text').format(
                amount=f"{last['amount']:,}",
                date=last['paid_at'].strftime('%d.%m.%Y'),
                method=last['payment_method'],
                period=last['billing_period'],
            )
        else:
            text = get_text(lang, 'message_text', 'no_payments')
        await message.answer(text=text, reply_markup=kb.payment_menu(lang))

    elif message.text == back_btn:
        await message.answer(
            text=get_text(lang, 'message_text', 'main_menu'),
            reply_markup=kb.main_menu(lang),
        )
        await state.set_state(UserState.main_menu)


# --- Payment method selection → send invoice ---

@router.message(UserState.payment_method)
async def payment_method_handler(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    lang = data.get('language', '🇺🇿 uz')
    back_btn = get_text(lang, 'buttons', 'back')

    if message.text == back_btn:
        await message.answer(
            text=get_text(lang, 'message_text', 'payment_menu_text'),
            reply_markup=kb.payment_menu(lang),
        )
        await state.set_state(UserState.payment_menu)
        return

    if message.text == "💳 Click":
        user = await get_user(message.from_user.id)
        if not user:
            return
        billing_period = user['payments_completed'] + 1
        await send_click_invoice(bot, message.chat.id, billing_period, lang)

    elif message.text == "💳 Payme":
        user = await get_user(message.from_user.id)
        if not user:
            return
        billing_period = user['payments_completed'] + 1
        await send_payme_invoice(bot, message.chat.id, billing_period, lang)


# --- Telegram Payments callbacks (work for ANY state, no FSM filter) ---

@router.pre_checkout_query()
async def on_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    """Telegram sends this when user clicks 'Pay'. Must respond within 10 seconds."""
    payload = pre_checkout_query.invoice_payload
    parts = payload.split("_")

    if len(parts) == 3:
        # Legacy: "click_123456_1"
        telegram_id = int(parts[1])
        user = await get_user(telegram_id)
        if not user:
            await pre_checkout_query.answer(ok=False, error_message="User not found")
            return
        if user['payments_completed'] >= MONTHS_COUNT:
            await pre_checkout_query.answer(ok=False, error_message="All payments already completed")
            return

    elif len(parts) == 4 and parts[2].startswith("c"):
        # Course: "click_123456_c5_2"
        telegram_id = int(parts[1])
        course_id = int(parts[2][1:])
        user = await get_user(telegram_id)
        if not user:
            await pre_checkout_query.answer(ok=False, error_message="User not found")
            return
        course = await get_course(course_id)
        if not course:
            await pre_checkout_query.answer(ok=False, error_message="Course not found")
            return
        enrollment = await get_user_enrollment_by_telegram(telegram_id, course_id)
        if enrollment and enrollment['payments_completed'] >= course['months_count']:
            await pre_checkout_query.answer(ok=False, error_message="All payments already completed")
            return
    else:
        await pre_checkout_query.answer(ok=False, error_message="Invalid payment data")
        return

    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def on_successful_payment(message: Message, state: FSMContext, bot: Bot):
    """Telegram sends this after payment is confirmed by the provider."""
    payment_info = message.successful_payment
    payload = payment_info.invoice_payload
    parts = payload.split("_")

    method = parts[0]  # "click" or "payme"
    telegram_id = int(parts[1])

    user = await get_user(telegram_id)
    if not user:
        return

    data = await state.get_data()
    lang = data.get('language', user['language'])
    transaction_id = payment_info.telegram_payment_charge_id

    if len(parts) == 3:
        # Legacy flow: "click_123456_1"
        billing_period = int(parts[2])

        await create_payment(
            user_id=user['id'],
            amount=MONTHLY_PAYMENT,
            payment_method=method,
            transaction_id=transaction_id,
            billing_period=billing_period,
        )

        next_billing = date.today() + timedelta(days=30)
        await update_user_billing(
            telegram_id=telegram_id,
            next_billing_date=next_billing if billing_period < MONTHS_COUNT else None,
            payments_completed=billing_period,
        )

        await message.answer(
            text=get_text(lang, 'message_text', 'payment_success').format(
                amount=f"{MONTHLY_PAYMENT:,}",
                period=billing_period,
            ),
        )

        if billing_period == 1 and GROUP_ID:
            try:
                invite = await bot.create_chat_invite_link(
                    chat_id=GROUP_ID, member_limit=1,
                )
                await message.answer(
                    text=get_text(lang, 'message_text', 'group_invite').format(
                        link=invite.invite_link,
                    ),
                )
            except Exception:
                pass

    elif len(parts) == 4 and parts[2].startswith("c"):
        # Course flow: "click_123456_c5_2"
        course_id = int(parts[2][1:])
        billing_period = int(parts[3])

        course = await get_course(course_id)
        if not course:
            return

        await create_payment_for_course(
            user_id=user['id'],
            amount=course['monthly_amount'],
            payment_method=method,
            transaction_id=transaction_id,
            billing_period=billing_period,
            course_id=course_id,
        )

        enrollment = await get_user_enrollment_by_telegram(telegram_id, course_id)
        if not enrollment:
            next_bill = date.today() + timedelta(days=30) if 1 < course['months_count'] else None
            enrollment = await enroll_user(user['id'], course_id, next_bill)
            await update_enrollment_billing(
                enrollment['id'],
                paid_amount=course['monthly_amount'],
                payments_completed=1,
                next_billing_date=next_bill,
            )
        else:
            new_paid = enrollment['paid_amount'] + course['monthly_amount']
            new_completed = enrollment['payments_completed'] + 1
            next_bill = date.today() + timedelta(days=30) if new_completed < course['months_count'] else None
            await update_enrollment_billing(
                enrollment['id'], new_paid, new_completed, next_bill,
            )

        await message.answer(
            text=get_text(lang, 'message_text', 'course_payment_success').format(
                title=course['title'],
                amount=f"{course['monthly_amount']:,}",
                period=billing_period,
                total=course['months_count'],
            ),
        )

        # Send one-time group invite on first payment
        course_group_id = course.get('group_id')
        if billing_period == 1 and course_group_id:
            try:
                invite = await bot.create_chat_invite_link(
                    chat_id=course_group_id, member_limit=1,
                )
                await message.answer(
                    text=get_text(lang, 'message_text', 'group_invite').format(
                        link=invite.invite_link,
                    ),
                )
            except Exception:
                pass

    # Return to main menu
    await message.answer(
        text=get_text(lang, 'message_text', 'main_menu'),
        reply_markup=kb.main_menu(lang),
    )
    await state.set_state(UserState.main_menu)
