from aiogram.types import KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
import json


with open("data.json", "r", encoding="utf-8") as file:
    translations = json.load(file)



def get_text(lang, category, key):
    return translations.get(lang, {}).get(category, {}).get(key, f"[{key}]")



def start_key():
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text=f"🇺🇿 uz"),KeyboardButton(text=f"🇷🇺 ru"))
    keyboard.adjust(2)
    return keyboard.as_markup(resize_keyboard=True)