import json
from aiogram import Bot, Dispatcher, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove
from decouple import config 
from aiogram.enums import ChatAction
from aiogram import F
from aiogram.types import Message
from aiogram.fsm.state import default_state
from aiogram.filters import StateFilter
import datetime


#local modules
from states.language import LanguageState
from keyboards.start import start_key



TOKEN = config('TOKEN')
bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()





with open("data.json", "r", encoding="utf-8") as file:
    translations = json.load(file)


def get_text(lang, category, key):
    return translations.get(lang, {}).get(category, {}).get(key, f"[{key}]")


user_lang = {"uz":"🇺🇿 uz", "ru":"🇷🇺 ru"}


@router.message(F.text.startswith("/start"))
async def start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    await bot.send_message(
        chat_id=user_id,
        text=translations['start'],
        reply_markup=start_key(),
        parse_mode='HTML'
    )
    await state.set_state(LanguageState.language)