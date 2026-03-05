import json
from aiogram import Router, Bot
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from states import UserState
import keyboards as kb
from database.queries import (
    get_user, get_active_courses, get_course,
    get_user_enrollment_by_telegram, update_user_language,
)
from payments.click import send_click_invoice_for_course
from payments.payme import send_payme_invoice_for_course

router = Router()

with open("data.json", "r", encoding="utf-8") as file:
    translations = json.load(file)


def get_text(lang, category, key):
    return translations.get(lang, {}).get(category, {}).get(key, f"[{key}]")


@router.message(UserState.main_menu)
async def main_menu_handler(message: Message, state: FSMContext):
    print(f"user_tg_id: {message.from_user.id}")
    data = await state.get_data()
    lang = data.get('language', '🇺🇿 uz')

    payment_btn = get_text(lang, 'buttons', 'payment')
    my_info_btn = get_text(lang, 'buttons', 'my_info')
    contact_btn = get_text(lang, 'buttons', 'contact_us')

    if message.text == payment_btn:
        await message.answer(
            text=get_text(lang, 'message_text', 'payment_menu_text'),
            reply_markup=kb.payment_menu(lang),
        )
        await state.set_state(UserState.payment_menu)

    elif message.text == my_info_btn:
        user = await get_user(message.from_user.id)
        if user:
            text = get_text(lang, 'message_text', 'my_info_text').format(
                name=user['full_name'],
                phone=user['phone'],
            )
        else:
            text = "[User not found]"
        await message.answer(text=text, reply_markup=kb.back_button(lang))

    elif message.text == contact_btn:
        await message.answer(
            text=get_text(lang, 'message_text', 'contact_text'),
            reply_markup=kb.back_button(lang),
        )

    elif message.text == get_text(lang, 'buttons', 'change_language'):
        await message.answer(
            text=get_text(lang, 'message_text', 'select_language'),
            reply_markup=kb.start_key(),
        )
        await state.set_state(UserState.change_language)

    elif message.text == get_text(lang, 'buttons', 'courses'):
        courses = await get_active_courses()
        if not courses:
            await message.answer(
                text=get_text(lang, 'message_text', 'no_courses'),
                reply_markup=kb.main_menu(lang),
            )
            return
        await message.answer(
            text=get_text(lang, 'message_text', 'courses_list'),
            reply_markup=kb.course_list_keyboard(courses, lang),
        )
        await state.update_data(courses_cache={c['title']: c['id'] for c in courses})
        await state.set_state(UserState.course_list)

    elif message.text == get_text(lang, 'buttons', 'back'):
        await message.answer(
            text=get_text(lang, 'message_text', 'main_menu'),
            reply_markup=kb.main_menu(lang),
        )


# --- Course browsing ---

@router.message(UserState.course_list)
async def course_list_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get('language', '🇺🇿 uz')

    if message.text == get_text(lang, 'buttons', 'back'):
        await message.answer(
            text=get_text(lang, 'message_text', 'main_menu'),
            reply_markup=kb.main_menu(lang),
        )
        await state.set_state(UserState.main_menu)
        return

    courses_cache = data.get('courses_cache', {})
    course_id = courses_cache.get(message.text)
    if course_id is None:
        await message.answer(get_text(lang, 'message_text', 'course_not_found'))
        return

    course = await get_course(course_id)
    if not course:
        await message.answer(get_text(lang, 'message_text', 'course_not_found'))
        return

    enrollment = await get_user_enrollment_by_telegram(message.from_user.id, course_id)
    paid = enrollment['payments_completed'] if enrollment else 0

    text = get_text(lang, 'message_text', 'course_detail').format(
        title=course['title'],
        description=course.get('description', ''),
        start_date=course['start_date'].strftime('%d.%m.%Y'),
        end_date=course['end_date'].strftime('%d.%m.%Y'),
        total_amount=f"{course['total_amount']:,}",
        monthly_amount=f"{course['monthly_amount']:,}",
        months_count=course['months_count'],
        paid=paid,
        total_months=course['months_count'],
    )
    await message.answer(text=text, reply_markup=kb.course_detail_keyboard(lang))
    await state.update_data(selected_course_id=course_id)
    await state.set_state(UserState.course_detail)


@router.message(UserState.course_detail)
async def course_detail_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get('language', '🇺🇿 uz')

    if message.text == get_text(lang, 'buttons', 'back'):
        courses = await get_active_courses()
        if not courses:
            await message.answer(
                text=get_text(lang, 'message_text', 'main_menu'),
                reply_markup=kb.main_menu(lang),
            )
            await state.set_state(UserState.main_menu)
            return
        await message.answer(
            text=get_text(lang, 'message_text', 'courses_list'),
            reply_markup=kb.course_list_keyboard(courses, lang),
        )
        await state.update_data(courses_cache={c['title']: c['id'] for c in courses})
        await state.set_state(UserState.course_list)
        return

    if message.text == get_text(lang, 'buttons', 'pay_for_course'):
        course_id = data.get('selected_course_id')
        course = await get_course(course_id)
        enrollment = await get_user_enrollment_by_telegram(message.from_user.id, course_id)

        if enrollment and enrollment['payments_completed'] >= course['months_count']:
            await message.answer(get_text(lang, 'message_text', 'course_all_paid'))
            return

        await message.answer(
            text=get_text(lang, 'message_text', 'make_payment_text'),
            reply_markup=kb.payment_method_menu(lang),
        )
        await state.set_state(UserState.course_payment_method)


@router.message(UserState.course_payment_method)
async def course_payment_method_handler(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    lang = data.get('language', '🇺🇿 uz')

    if message.text == get_text(lang, 'buttons', 'back'):
        course_id = data.get('selected_course_id')
        course = await get_course(course_id)
        if course:
            enrollment = await get_user_enrollment_by_telegram(message.from_user.id, course_id)
            paid = enrollment['payments_completed'] if enrollment else 0
            text = get_text(lang, 'message_text', 'course_detail').format(
                title=course['title'],
                description=course.get('description', ''),
                start_date=course['start_date'].strftime('%d.%m.%Y'),
                end_date=course['end_date'].strftime('%d.%m.%Y'),
                total_amount=f"{course['total_amount']:,}",
                monthly_amount=f"{course['monthly_amount']:,}",
                months_count=course['months_count'],
                paid=paid,
                total_months=course['months_count'],
            )
            await message.answer(text=text, reply_markup=kb.course_detail_keyboard(lang))
        await state.set_state(UserState.course_detail)
        return

    course_id = data.get('selected_course_id')
    course = await get_course(course_id)
    if not course:
        return

    enrollment = await get_user_enrollment_by_telegram(message.from_user.id, course_id)
    billing_period = (enrollment['payments_completed'] + 1) if enrollment else 1

    if message.text == "💳 Click":
        await send_click_invoice_for_course(bot, message.chat.id, course, billing_period, lang)
    elif message.text == "💳 Payme":
        await send_payme_invoice_for_course(bot, message.chat.id, course, billing_period, lang)


# --- Language change ---

@router.message(UserState.change_language)
async def change_language_handler(message: Message, state: FSMContext):
    if message.text not in ("🇺🇿 uz", "🇷🇺 ru"):
        data = await state.get_data()
        lang = data.get('language', '🇺🇿 uz')
        await message.answer(
            text=get_text(lang, 'message_text', 'select_language'),
            reply_markup=kb.start_key(),
        )
        return

    new_lang = message.text
    await state.update_data(language=new_lang)
    await update_user_language(message.from_user.id, new_lang)

    await message.answer(
        text=get_text(new_lang, 'message_text', 'language_changed'),
    )
    await message.answer(
        text=get_text(new_lang, 'message_text', 'main_menu'),
        reply_markup=kb.main_menu(new_lang),
    )
    await state.set_state(UserState.main_menu)
