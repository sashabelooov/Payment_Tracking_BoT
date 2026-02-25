import json
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from states import UserState
import keyboards as kb
from database.queries import create_user, get_user

router = Router()

with open("data.json", "r", encoding="utf-8") as file:
    translations = json.load(file)


def get_text(lang, category, key):
    return translations.get(lang, {}).get(category, {}).get(key, f"[{key}]")


@router.message(F.text.startswith("/start"))
async def start(message: Message, state: FSMContext):
    await state.clear()
    existing_user = await get_user(message.from_user.id)
    if existing_user and existing_user['is_active']:
        lang = existing_user['language']
        await message.answer(
            text=get_text(lang, 'message_text', 'main_menu'),
            reply_markup=kb.main_menu(lang),
        )
        await state.update_data(language=lang)
        await state.set_state(UserState.main_menu)
        return

    await message.answer(
        text=translations['start'],
        reply_markup=kb.start_key(),
        parse_mode='HTML',
    )
    await state.set_state(UserState.language)


@router.message(UserState.language)
async def ask_phone(message: Message, state: FSMContext):
    if message.text not in ("🇺🇿 uz", "🇷🇺 ru"):
        return
    await state.update_data(language=message.text)
    lang = message.text
    await message.answer(
        text=get_text(lang, 'message_text', 'phone'),
        reply_markup=kb.ask_phone(lang),
    )
    await state.set_state(UserState.phone)


@router.message(UserState.phone)
async def check_phone(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data['language']

    phone = None
    if message.contact:
        phone = message.contact.phone_number
        if not phone.startswith("+"):
            phone = "+" + phone
    elif message.text:
        text = message.text
        if text.startswith("+998") and len(text) == 13 and text[1:].isdigit():
            phone = text

    if phone is None:
        await message.answer(text=get_text(lang, 'message_text', 'error_phone'))
        return

    await state.update_data(phone=phone)
    await message.answer(
        text=get_text(lang, 'message_text', 'name'),
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(UserState.fio)


@router.message(UserState.fio)
async def fio_user(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data['language']

    name = message.text.strip()
    if not all(c.isalpha() or c.isspace() for c in name):
        await message.answer(text=get_text(lang, 'message_text', 'error_name'))
        return

    await state.update_data(user_name=name)
    data = await state.get_data()
    confirm_text = (
        get_text(lang, 'message_text', 'confirmed_userinfo')
        + get_text(lang, 'message_text', 'conf_name') + data['user_name'] + "\n"
        + get_text(lang, 'message_text', 'conf_phone') + data['phone']
    )
    await message.answer(text=confirm_text, reply_markup=kb.conf(lang))
    await state.set_state(UserState.confirm)


@router.message(UserState.confirm)
async def confirm_registration(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data['language']
    confirm_btn = get_text(lang, 'buttons', 'confirm')
    reject_btn = get_text(lang, 'buttons', 'rejected')

    if message.text == confirm_btn:
        await create_user(
            telegram_id=message.from_user.id,
            full_name=data['user_name'],
            phone=data['phone'],
            language=lang,
        )
        await message.answer(
            text=get_text(lang, 'message_text', 'registered'),
            reply_markup=kb.main_menu(lang),
        )
        await state.set_state(UserState.main_menu)

    elif message.text == reject_btn:
        await state.clear()
        await message.answer(
            text=get_text(lang, 'message_text', 'registration_cancelled'),
            reply_markup=ReplyKeyboardRemove(),
        )
