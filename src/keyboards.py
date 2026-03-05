import json
from aiogram.types import KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

with open("data.json", "r", encoding="utf-8") as file:
    translations = json.load(file)


def get_text(lang, category, key):
    return translations.get(lang, {}).get(category, {}).get(key, f"[{key}]")


def start_key():
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="🇺🇿 uz"), KeyboardButton(text="🇷🇺 ru"))
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)


def ask_phone(lang):
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text=get_text(lang, 'buttons', 'contact'), request_contact=True))
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True)


def conf(lang):
    kb = ReplyKeyboardBuilder()
    kb.add(
        KeyboardButton(text=get_text(lang, 'buttons', 'confirm')),
        KeyboardButton(text=get_text(lang, 'buttons', 'rejected')),
    )
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)


def main_menu(lang):
    kb = ReplyKeyboardBuilder()
    kb.add(
        KeyboardButton(text=get_text(lang, 'buttons', 'payment')),
        KeyboardButton(text=get_text(lang, 'buttons', 'my_info')),
        KeyboardButton(text=get_text(lang, 'buttons', 'courses')),
        KeyboardButton(text=get_text(lang, 'buttons', 'contact_us')),
        KeyboardButton(text=get_text(lang, 'buttons', 'change_language')),
    )
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)


def payment_menu(lang):
    kb = ReplyKeyboardBuilder()
    kb.add(
        KeyboardButton(text=get_text(lang, 'buttons', 'make_payment')),
        KeyboardButton(text=get_text(lang, 'buttons', 'last_billing')),
        KeyboardButton(text=get_text(lang, 'buttons', 'back')),
    )
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)


def payment_method_menu(lang):
    kb = ReplyKeyboardBuilder()
    kb.add(
        KeyboardButton(text="💳 Click"),
        KeyboardButton(text="💳 Payme"),
        KeyboardButton(text=get_text(lang, 'buttons', 'back')),
    )
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)


def back_button(lang):
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text=get_text(lang, 'buttons', 'back')))
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True)


def admin_back():
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="⬅️ Orqaga"))
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True)


def admin_menu(is_main_admin=False):
    kb = ReplyKeyboardBuilder()
    kb.add(
        KeyboardButton(text="💰 To'lov"),
        KeyboardButton(text="👥 Foydalanuvchilar"),
        KeyboardButton(text="📊 Statistika"),
        KeyboardButton(text="📝 Kurs yaratish"),
        KeyboardButton(text="📥 Excelga yuklash"),
        KeyboardButton(text="📢 Xabar yuborish"),
        KeyboardButton(text="🚫 Guruhdan chiqarish"),
        KeyboardButton(text="🌐 Tilni o'zgartirish"),
    )
    if is_main_admin:
        kb.add(
            KeyboardButton(text="➕ Admin qo'shish"),
            KeyboardButton(text="➖ Admin o'chirish"),
        )
    kb.add(KeyboardButton(text="⬅️ Chiqish"))
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)


def admin_pay_method():
    kb = ReplyKeyboardBuilder()
    kb.add(
        KeyboardButton(text="💵 Naqd"),
        KeyboardButton(text="💳 Karta"),
        KeyboardButton(text="⬅️ Orqaga"),
    )
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)


def admin_confirm():
    kb = ReplyKeyboardBuilder()
    kb.add(
        KeyboardButton(text="✅ Tasdiqlash"),
        KeyboardButton(text="❌ Bekor qilish"),
    )
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)


def admin_list_keyboard(admins: list):
    """Dynamic keyboard to select an admin to remove."""
    kb = ReplyKeyboardBuilder()
    for admin in admins:
        kb.add(KeyboardButton(text=f"{admin['telegram_id']}"))
    kb.add(KeyboardButton(text="⬅️ Orqaga"))
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True)


def course_list_keyboard(courses: list, lang: str):
    """Dynamic keyboard with one button per active course + back."""
    kb = ReplyKeyboardBuilder()
    for course in courses:
        kb.add(KeyboardButton(text=course['title']))
    kb.add(KeyboardButton(text=get_text(lang, 'buttons', 'back')))
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True)


def course_detail_keyboard(lang):
    """Pay for course + back."""
    kb = ReplyKeyboardBuilder()
    kb.add(
        KeyboardButton(text=get_text(lang, 'buttons', 'pay_for_course')),
        KeyboardButton(text=get_text(lang, 'buttons', 'back')),
    )
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)


def admin_course_select_keyboard(courses: list):
    """Dynamic keyboard for admin to select a course for export."""
    kb = ReplyKeyboardBuilder()
    for course in courses:
        kb.add(KeyboardButton(text=course['title']))
    kb.add(KeyboardButton(text="⬅️ Orqaga"))
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True)
