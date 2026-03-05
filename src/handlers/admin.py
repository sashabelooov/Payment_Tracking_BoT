import os
import tempfile
from datetime import datetime, date, timedelta

from aiogram import Router, F, Bot
from aiogram.types import Message, ReplyKeyboardRemove, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command

from states import AdminState, UserState
import keyboards as kb
from config import ADMIN_IDS
from database.queries import (
    get_all_users, get_payment_stats, deactivate_user,
    create_course, get_all_courses, get_course,
    get_course_enrollments_with_users, update_user_language,
    is_bot_admin, get_bot_admins, add_bot_admin, remove_bot_admin,
    get_user_by_phone, get_active_courses, enroll_user,
    get_user_enrollment_by_telegram, update_enrollment_billing,
    create_admin_payment, get_user_enrollments_with_courses,
)

router = Router()


def is_main_admin(user_id: int) -> bool:
    """Main admins from .env — can add/remove other admins."""
    return user_id in ADMIN_IDS


async def is_admin(user_id: int) -> bool:
    """Check if user is main admin or DB admin."""
    if user_id in ADMIN_IDS:
        return True
    return await is_bot_admin(user_id)


async def _go_admin_menu(message: Message, state: FSMContext):
    """Helper to return to admin menu."""
    main = is_main_admin(message.from_user.id)
    await message.answer("🔧 Admin panel", reply_markup=kb.admin_menu(main))
    await state.set_state(AdminState.menu)


@router.message(Command("adminpanel"))
async def admin_command(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ Sizda admin huquqi yo'q.")
        return
    await state.clear()
    main = is_main_admin(message.from_user.id)
    await message.answer(
        text="🔧 Admin panel",
        reply_markup=kb.admin_menu(main),
    )
    await state.set_state(AdminState.menu)


@router.message(AdminState.menu)
async def admin_menu_handler(message: Message, state: FSMContext, bot: Bot):
    if not await is_admin(message.from_user.id):
        return

    if message.text == "👥 Foydalanuvchilar":
        users = await get_all_users(active_only=False)
        if not users:
            await message.answer("Foydalanuvchilar topilmadi.")
            return

        lines = []
        for i, u in enumerate(users, 1):
            status = "✅" if u['is_active'] else "❌"
            lines.append(
                f"{i}. {status} {u['full_name']} | {u['phone']} | "
                f"To'lovlar: {u['payments_completed']}/3"
            )
        text = "👥 Foydalanuvchilar ro'yxati:\n\n" + "\n".join(lines)

        if len(text) > 4000:
            for chunk_start in range(0, len(text), 4000):
                await message.answer(text[chunk_start:chunk_start + 4000])
        else:
            await message.answer(text)

    elif message.text == "📊 Statistika":
        stats = await get_payment_stats()
        text = (
            "📊 Statistika:\n\n"
            f"👥 Faol foydalanuvchilar: {stats['total_active_users']}\n"
            f"💰 Jami to'lovlar: {stats['total_payments_collected']:,} so'm\n"
            f"⚠️ Muddati o'tganlar: {stats['overdue_users']}"
        )
        await message.answer(text)

    elif message.text == "📢 Xabar yuborish":
        await message.answer(
            "Barcha foydalanuvchilarga yuboriladigan xabarni yozing:",
            reply_markup=kb.admin_back(),
        )
        await state.set_state(AdminState.broadcast)

    elif message.text == "📝 Kurs yaratish":
        await message.answer(
            "Kurs nomini kiriting:",
            reply_markup=kb.admin_back(),
        )
        await state.set_state(AdminState.course_title)

    elif message.text == "📥 Excelga yuklash":
        courses = await get_all_courses()
        if not courses:
            await message.answer("📭 Kurslar mavjud emas.")
            return
        await message.answer(
            "Qaysi kursni eksport qilmoqchisiz?",
            reply_markup=kb.admin_course_select_keyboard(courses),
        )
        await state.update_data(courses_cache={c['title']: c['id'] for c in courses})
        await state.set_state(AdminState.export_select_course)

    elif message.text == "🌐 Tilni o'zgartirish":
        await message.answer(
            "🌐 Tilni tanlang:",
            reply_markup=kb.start_key(),
        )
        await state.set_state(AdminState.change_language)

    elif message.text == "💰 To'lov":
        await message.answer(
            "To'lov usulini tanlang:",
            reply_markup=kb.admin_pay_method(),
        )
        await state.set_state(AdminState.pay_method)

    elif message.text == "🚫 Guruhdan chiqarish":
        await message.answer(
            "Foydalanuvchi telefon raqamini kiriting:\nMisol: +998901234567",
            reply_markup=kb.admin_back(),
        )
        await state.set_state(AdminState.kick_phone)

    elif message.text == "➕ Admin qo'shish":
        if not is_main_admin(message.from_user.id):
            await message.answer("⛔ Faqat asosiy adminlar admin qo'sha oladi.")
            return
        await message.answer(
            "Yangi admin telefon raqamini kiriting:\n"
            "(Foydalanuvchi avval botda ro'yxatdan o'tgan bo'lishi kerak)\n\n"
            "Misol: +998901234567",
            reply_markup=kb.admin_back(),
        )
        await state.set_state(AdminState.add_admin_phone)

    elif message.text == "➖ Admin o'chirish":
        if not is_main_admin(message.from_user.id):
            await message.answer("⛔ Faqat asosiy adminlar admin o'chira oladi.")
            return
        admins = await get_bot_admins()
        if not admins:
            await message.answer("📭 Qo'shilgan adminlar yo'q.")
            return
        # Build display with user info
        lines = []
        for a in admins:
            lines.append(f"ID: {a['telegram_id']}")
        await message.answer(
            "O'chirmoqchi bo'lgan admin ID sini tanlang:\n\n" + "\n".join(lines),
            reply_markup=kb.admin_list_keyboard(admins),
        )
        await state.set_state(AdminState.remove_admin_select)

    elif message.text == "⬅️ Chiqish":
        await state.clear()
        await message.answer(
            "Admin paneldan chiqildi.",
            reply_markup=ReplyKeyboardRemove(),
        )


@router.message(AdminState.broadcast)
async def broadcast_handler(message: Message, state: FSMContext, bot: Bot):
    if not await is_admin(message.from_user.id):
        return
    if message.text == "⬅️ Orqaga":
        await _go_admin_menu(message, state)
        return

    users = await get_all_users(active_only=True)
    sent = 0
    failed = 0
    for user in users:
        try:
            await bot.send_message(chat_id=user['telegram_id'], text=message.text)
            sent += 1
        except Exception:
            failed += 1

    await message.answer(
        f"📢 Xabar yuborildi!\n✅ Yuborildi: {sent}\n❌ Xatolik: {failed}",
    )
    await _go_admin_menu(message, state)


# --- Course creation FSM ---

@router.message(AdminState.course_title)
async def course_title_handler(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    if message.text == "⬅️ Orqaga":
        await _go_admin_menu(message, state)
        return
    title = message.text.strip()
    if not title or len(title) > 200:
        await message.answer("Kurs nomini to'g'ri kiriting (1-200 belgi):")
        return
    await state.update_data(course_title=title)
    await message.answer("Kurs tavsifini kiriting:", reply_markup=kb.admin_back())
    await state.set_state(AdminState.course_description)


@router.message(AdminState.course_description)
async def course_description_handler(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    if message.text == "⬅️ Orqaga":
        await message.answer("Kurs nomini kiriting:", reply_markup=kb.admin_back())
        await state.set_state(AdminState.course_title)
        return
    description = message.text.strip()
    if not description:
        await message.answer("Iltimos, kurs tavsifini kiriting:")
        return
    await state.update_data(course_description=description)
    await message.answer("Boshlanish sanasini kiriting (DD.MM.YYYY):\nMisol: 02.04.2026", reply_markup=kb.admin_back())
    await state.set_state(AdminState.course_start_date)


@router.message(AdminState.course_start_date)
async def course_start_handler(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    if message.text == "⬅️ Orqaga":
        await message.answer("Kurs tavsifini kiriting:", reply_markup=kb.admin_back())
        await state.set_state(AdminState.course_description)
        return
    try:
        start_date = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
    except ValueError:
        await message.answer("Sanani to'g'ri formatda kiriting (DD.MM.YYYY):\nMisol: 02.04.2026")
        return
    await state.update_data(course_start=start_date.isoformat())
    await message.answer("Tugash sanasini kiriting (DD.MM.YYYY):\nMisol: 02.07.2026", reply_markup=kb.admin_back())
    await state.set_state(AdminState.course_end_date)


@router.message(AdminState.course_end_date)
async def course_end_handler(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    if message.text == "⬅️ Orqaga":
        await message.answer("Boshlanish sanasini kiriting (DD.MM.YYYY):\nMisol: 02.04.2026", reply_markup=kb.admin_back())
        await state.set_state(AdminState.course_start_date)
        return
    try:
        end_date = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
    except ValueError:
        await message.answer("Sanani to'g'ri formatda kiriting (DD.MM.YYYY):\nMisol: 02.07.2026")
        return
    data = await state.get_data()
    start_date = datetime.fromisoformat(data['course_start']).date()
    if end_date <= start_date:
        await message.answer("Tugash sanasi boshlanish sanasidan keyin bo'lishi kerak!")
        return
    await state.update_data(course_end=end_date.isoformat())
    await message.answer("Necha oyga to'lov bo'linsin? (raqam kiriting):\nMisol: 3", reply_markup=kb.admin_back())
    await state.set_state(AdminState.course_months_count)


@router.message(AdminState.course_months_count)
async def course_months_handler(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    if message.text == "⬅️ Orqaga":
        await message.answer("Tugash sanasini kiriting (DD.MM.YYYY):\nMisol: 02.07.2026", reply_markup=kb.admin_back())
        await state.set_state(AdminState.course_end_date)
        return
    try:
        months = int(message.text.strip())
        if months <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Iltimos, musbat son kiriting:\nMisol: 3")
        return
    await state.update_data(course_months=months)
    await message.answer("Kurs umumiy narxini kiriting (so'mda):\nMisol: 3000000", reply_markup=kb.admin_back())
    await state.set_state(AdminState.course_total_amount)


@router.message(AdminState.course_total_amount)
async def course_amount_handler(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    if message.text == "⬅️ Orqaga":
        await message.answer("Necha oyga to'lov bo'linsin? (raqam kiriting):\nMisol: 3", reply_markup=kb.admin_back())
        await state.set_state(AdminState.course_months_count)
        return
    try:
        total = int(message.text.strip().replace(" ", "").replace(",", ""))
        if total <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Iltimos, narxni to'g'ri kiriting:\nMisol: 3000000")
        return

    data = await state.get_data()
    await state.update_data(course_total=total, course_monthly=total // data['course_months'])
    await message.answer(
        "Guruh ID sini kiriting (raqam):\n\n"
        "💡 Guruh ID sini olish uchun @userinfobot ni guruhga qo'shing, "
        "u guruhning ID sini ko'rsatadi.\n\n"
        "Misol: -1001234567890",
        reply_markup=kb.admin_back(),
    )
    await state.set_state(AdminState.course_group_id)


@router.message(AdminState.course_group_id)
async def course_group_id_handler(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    if message.text == "⬅️ Orqaga":
        await message.answer("Kurs umumiy narxini kiriting (so'mda):\nMisol: 3000000", reply_markup=kb.admin_back())
        await state.set_state(AdminState.course_total_amount)
        return
    try:
        group_id = int(message.text.strip())
    except ValueError:
        await message.answer(
            "Iltimos, guruh ID sini raqam sifatida kiriting.\n"
            "Misol: -1001234567890\n\n"
            "💡 @userinfobot ni guruhga qo'shib, ID ni oling."
        )
        return
    await state.update_data(course_group_id=group_id)
    await message.answer(
        "Guruhga taklif havolasini kiriting:\n"
        "Misol: https://t.me/+abc123xyz",
        reply_markup=kb.admin_back(),
    )
    await state.set_state(AdminState.course_invite_link)


@router.message(AdminState.course_invite_link)
async def course_invite_link_handler(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    if message.text == "⬅️ Orqaga":
        await message.answer(
            "Guruh ID sini kiriting (raqam):\n\n"
            "💡 Guruh ID sini olish uchun @userinfobot ni guruhga qo'shing, "
            "u guruhning ID sini ko'rsatadi.\n\n"
            "Misol: -1001234567890",
            reply_markup=kb.admin_back(),
        )
        await state.set_state(AdminState.course_group_id)
        return
    invite_link = message.text.strip()
    if not invite_link.startswith("https://t.me/"):
        await message.answer(
            "Iltimos, to'g'ri Telegram havola kiriting.\n"
            "Misol: https://t.me/+abc123xyz"
        )
        return
    await state.update_data(course_invite_link=invite_link)

    data = await state.get_data()
    title = data['course_title']
    description = data.get('course_description', '')
    start = data['course_start']
    end = data['course_end']
    total = data['course_total']
    months = data['course_months']
    monthly = data['course_monthly']
    group_id = data['course_group_id']

    text = (
        f"Kursni tasdiqlaysizmi?\n\n"
        f"📚 {title}\n"
        f"📝 {description}\n"
        f"📅 {start} — {end}\n"
        f"💰 {total:,} so'm ({months} oy x {monthly:,} so'm)\n"
        f"👥 Guruh ID: {group_id}\n"
        f"🔗 Havola: {invite_link}"
    )
    await message.answer(text, reply_markup=kb.admin_confirm())
    await state.set_state(AdminState.course_confirm)


@router.message(AdminState.course_confirm)
async def course_confirm_handler(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return

    if message.text == "✅ Tasdiqlash":
        data = await state.get_data()
        start_date = datetime.fromisoformat(data['course_start']).date()
        end_date = datetime.fromisoformat(data['course_end']).date()

        await create_course(
            title=data['course_title'],
            description=data.get('course_description', ''),
            start_date=start_date,
            end_date=end_date,
            total_amount=data['course_total'],
            monthly_amount=data['course_monthly'],
            months_count=data['course_months'],
            group_id=data.get('course_group_id'),
            invite_link=data.get('course_invite_link', ''),
        )
        await message.answer("✅ Kurs muvaffaqiyatli yaratildi!")
        await _go_admin_menu(message, state)

    elif message.text == "❌ Bekor qilish":
        await message.answer("Kurs yaratish bekor qilindi.")
        await _go_admin_menu(message, state)


# --- Excel export ---

@router.message(AdminState.export_select_course)
async def export_course_handler(message: Message, state: FSMContext, bot: Bot):
    if not await is_admin(message.from_user.id):
        return

    if message.text == "⬅️ Orqaga":
        await _go_admin_menu(message, state)
        return

    data = await state.get_data()
    courses_cache = data.get('courses_cache', {})
    course_id = courses_cache.get(message.text)

    if course_id is None:
        await message.answer("Kurs topilmadi.")
        return

    enrollments = await get_course_enrollments_with_users(course_id)
    course = await get_course(course_id)

    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = course['title'][:31]

    ws.append(["#", "F.I.O.", "Telefon", "Telegram ID",
               "To'langan", "Qolgan", "To'lovlar", "Holat", "Ro'yxatdan o'tgan"])

    for i, e in enumerate(enrollments, 1):
        remaining = course['total_amount'] - e['paid_amount']
        status = "✅ To'liq" if e['payments_completed'] >= course['months_count'] else "⏳ Jarayonda"
        ws.append([
            i, e['full_name'], e['phone'], e['telegram_id'],
            e['paid_amount'], remaining,
            f"{e['payments_completed']}/{course['months_count']}",
            status, e['enrolled_at'].strftime('%d.%m.%Y'),
        ])

    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = max_len + 2

    filepath = os.path.join(tempfile.gettempdir(), f"{course['title']}_export.xlsx")
    wb.save(filepath)

    try:
        doc = FSInputFile(filepath, filename=f"{course['title']}.xlsx")
        await message.answer_document(doc, caption=f"📊 {course['title']} — eksport")
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

    await _go_admin_menu(message, state)


# --- Admin language change ---

@router.message(AdminState.change_language)
async def admin_change_language_handler(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return

    if message.text not in ("🇺🇿 uz", "🇷🇺 ru"):
        await message.answer(
            "🌐 Tilni tanlang:",
            reply_markup=kb.start_key(),
        )
        return

    new_lang = message.text
    await state.update_data(language=new_lang)
    await update_user_language(message.from_user.id, new_lang)

    if new_lang == "🇺🇿 uz":
        await message.answer("✅ Til muvaffaqiyatli o'zgartirildi!")
    else:
        await message.answer("✅ Язык успешно изменён!")

    await _go_admin_menu(message, state)


# --- Admin Payment FSM ---

@router.message(AdminState.pay_method)
async def admin_pay_method_handler(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    if message.text == "⬅️ Orqaga":
        await _go_admin_menu(message, state)
        return

    if message.text in ("💵 Naqd", "💳 Karta"):
        method = "cash" if message.text == "💵 Naqd" else "card"
        await state.update_data(pay_method=method)

        courses = await get_active_courses()
        if not courses:
            await message.answer("📭 Faol kurslar mavjud emas.")
            await _go_admin_menu(message, state)
            return
        await message.answer(
            "Kursni tanlang:",
            reply_markup=kb.admin_course_select_keyboard(courses),
        )
        await state.update_data(courses_cache={c['title']: c['id'] for c in courses})
        await state.set_state(AdminState.pay_course)
    else:
        await message.answer("Iltimos, to'lov usulini tanlang:", reply_markup=kb.admin_pay_method())


@router.message(AdminState.pay_course)
async def admin_pay_course_handler(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    if message.text == "⬅️ Orqaga":
        await message.answer("To'lov usulini tanlang:", reply_markup=kb.admin_pay_method())
        await state.set_state(AdminState.pay_method)
        return

    data = await state.get_data()
    courses_cache = data.get('courses_cache', {})
    course_id = courses_cache.get(message.text)

    if course_id is None:
        await message.answer("Kurs topilmadi. Ro'yxatdan tanlang.")
        return

    await state.update_data(pay_course_id=course_id, pay_course_title=message.text)
    await message.answer(
        "Talaba telefon raqamini kiriting:\nMisol: +998901234567",
        reply_markup=kb.admin_back(),
    )
    await state.set_state(AdminState.pay_phone)


@router.message(AdminState.pay_phone)
async def admin_pay_phone_handler(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    if message.text == "⬅️ Orqaga":
        data = await state.get_data()
        courses = await get_active_courses()
        await message.answer(
            "Kursni tanlang:",
            reply_markup=kb.admin_course_select_keyboard(courses),
        )
        await state.update_data(courses_cache={c['title']: c['id'] for c in courses})
        await state.set_state(AdminState.pay_course)
        return

    phone = message.text.strip()
    user = await get_user_by_phone(phone)
    if not user:
        await message.answer(
            "❌ Bu telefon raqamli foydalanuvchi topilmadi.\n"
            "Foydalanuvchi avval botda /start orqali ro'yxatdan o'tishi kerak.\n\n"
            "Qaytadan kiriting yoki ⬅️ Orqaga bosing."
        )
        return

    await state.update_data(
        pay_user_id=user['id'],
        pay_telegram_id=user['telegram_id'],
        pay_user_name=user['full_name'],
        pay_user_phone=user['phone'],
    )
    await message.answer(
        f"✅ Talaba topildi: {user['full_name']} ({user['phone']})\n\n"
        "To'lov miqdorini kiriting (so'mda):\nMisol: 1000000",
        reply_markup=kb.admin_back(),
    )
    await state.set_state(AdminState.pay_amount)


@router.message(AdminState.pay_amount)
async def admin_pay_amount_handler(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    if message.text == "⬅️ Orqaga":
        await message.answer(
            "Talaba telefon raqamini kiriting:\nMisol: +998901234567",
            reply_markup=kb.admin_back(),
        )
        await state.set_state(AdminState.pay_phone)
        return

    try:
        amount = int(message.text.strip().replace(" ", "").replace(",", ""))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Iltimos, to'lov miqdorini to'g'ri kiriting:\nMisol: 1000000")
        return

    await state.update_data(pay_amount=amount)
    await message.answer(
        "📸 Kvitansiya (chek) rasmini yuboring:",
        reply_markup=kb.admin_back(),
    )
    await state.set_state(AdminState.pay_receipt)


@router.message(AdminState.pay_receipt)
async def admin_pay_receipt_handler(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return

    if message.text == "⬅️ Orqaga":
        await message.answer(
            "To'lov miqdorini kiriting (so'mda):\nMisol: 1000000",
            reply_markup=kb.admin_back(),
        )
        await state.set_state(AdminState.pay_amount)
        return

    if not message.photo:
        await message.answer("Iltimos, rasm yuboring (kvitansiya/chek):")
        return

    # Get the highest resolution photo
    receipt_file_id = message.photo[-1].file_id
    await state.update_data(pay_receipt_file_id=receipt_file_id)

    data = await state.get_data()
    text = (
        f"To'lovni tasdiqlaysizmi?\n\n"
        f"📚 Kurs: {data['pay_course_title']}\n"
        f"👤 Talaba: {data['pay_user_name']}\n"
        f"📞 Telefon: {data['pay_user_phone']}\n"
        f"💰 Miqdor: {data['pay_amount']:,} so'm\n"
        f"💳 Usul: {'Naqd' if data['pay_method'] == 'cash' else 'Karta'}\n"
        f"📸 Kvitansiya: ✅"
    )
    await message.answer(text, reply_markup=kb.admin_confirm())
    await state.set_state(AdminState.pay_confirm)


@router.message(AdminState.pay_confirm)
async def admin_pay_confirm_handler(message: Message, state: FSMContext, bot: Bot):
    if not await is_admin(message.from_user.id):
        return

    if message.text == "❌ Bekor qilish":
        await message.answer("To'lov bekor qilindi.")
        await _go_admin_menu(message, state)
        return

    if message.text != "✅ Tasdiqlash":
        await message.answer("Iltimos, tasdiqlang yoki bekor qiling:", reply_markup=kb.admin_confirm())
        return

    data = await state.get_data()
    user_id = data['pay_user_id']
    telegram_id = data['pay_telegram_id']
    course_id = data['pay_course_id']
    amount = data['pay_amount']
    method = data['pay_method']
    receipt_file_id = data.get('pay_receipt_file_id')

    course = await get_course(course_id)
    if not course:
        await message.answer("❌ Kurs topilmadi.")
        await _go_admin_menu(message, state)
        return

    # Get or create enrollment
    enrollment = await get_user_enrollment_by_telegram(telegram_id, course_id)
    if not enrollment:
        next_bill = date.today() + timedelta(days=30) if 1 < course['months_count'] else None
        enrollment = await enroll_user(user_id, course_id, next_bill)
        billing_period = 1
        new_paid = amount
        new_completed = 1
    else:
        billing_period = enrollment['payments_completed'] + 1
        new_paid = enrollment['paid_amount'] + amount
        new_completed = enrollment['payments_completed'] + 1

    next_bill = date.today() + timedelta(days=30) if new_completed < course['months_count'] else None

    # Save payment
    await create_admin_payment(
        user_id=user_id,
        amount=amount,
        payment_method=method,
        billing_period=billing_period,
        course_id=course_id,
        receipt_file_id=receipt_file_id,
    )

    # Update enrollment
    await update_enrollment_billing(
        enrollment['id'], new_paid, new_completed, next_bill,
    )

    await message.answer(
        f"✅ To'lov muvaffaqiyatli saqlandi!\n\n"
        f"📚 {course['title']}\n"
        f"👤 {data['pay_user_name']}\n"
        f"💰 {amount:,} so'm\n"
        f"📊 To'lov: {new_completed}/{course['months_count']}"
    )

    # Send one-time group invite on first payment
    course_group_id = course.get('group_id')
    if billing_period == 1 and course_group_id:
        try:
            invite = await bot.create_chat_invite_link(
                chat_id=course_group_id, member_limit=1,
            )
            # Send invite to the student
            await bot.send_message(
                chat_id=telegram_id,
                text=f"🔗 Yopiq guruhga qo'shilish uchun havola:\n{invite.invite_link}\n\n⚠️ Bu havola faqat siz uchun!",
            )
            await message.answer(f"🔗 Talabaga guruh havolasi yuborildi.")
        except Exception:
            await message.answer("⚠️ Guruh havolasini yuborishda xatolik.")

    await _go_admin_menu(message, state)


# --- Add/Remove Admin ---

@router.message(AdminState.add_admin_phone)
async def add_admin_phone_handler(message: Message, state: FSMContext):
    if not is_main_admin(message.from_user.id):
        return
    if message.text == "⬅️ Orqaga":
        await _go_admin_menu(message, state)
        return

    phone = message.text.strip()
    user = await get_user_by_phone(phone)
    if not user:
        await message.answer(
            "❌ Bu telefon raqamli foydalanuvchi topilmadi.\n"
            "Foydalanuvchi avval botda /start orqali ro'yxatdan o'tishi kerak.\n\n"
            "Qaytadan kiriting yoki ⬅️ Orqaga bosing."
        )
        return

    if user['telegram_id'] in ADMIN_IDS:
        await message.answer("Bu foydalanuvchi allaqachon asosiy admin.")
        await _go_admin_menu(message, state)
        return

    result = await add_bot_admin(user['telegram_id'], message.from_user.id)
    if result:
        await message.answer(
            f"✅ {user['full_name']} ({user['phone']}) admin sifatida qo'shildi!\n"
            f"Telegram ID: {user['telegram_id']}"
        )
    else:
        await message.answer(f"⚠️ {user['full_name']} allaqachon admin.")

    await _go_admin_menu(message, state)


@router.message(AdminState.remove_admin_select)
async def remove_admin_select_handler(message: Message, state: FSMContext):
    if not is_main_admin(message.from_user.id):
        return
    if message.text == "⬅️ Orqaga":
        await _go_admin_menu(message, state)
        return

    try:
        admin_tid = int(message.text.strip())
    except ValueError:
        await message.answer("Iltimos, ro'yxatdan tanlang.")
        return

    await remove_bot_admin(admin_tid)
    await message.answer(f"✅ Admin (ID: {admin_tid}) o'chirildi.")
    await _go_admin_menu(message, state)


# --- Kick user from group ---

@router.message(AdminState.kick_phone)
async def kick_phone_handler(message: Message, state: FSMContext, bot: Bot):
    if not await is_admin(message.from_user.id):
        return
    if message.text == "⬅️ Orqaga":
        await _go_admin_menu(message, state)
        return

    phone = message.text.strip()
    user = await get_user_by_phone(phone)
    if not user:
        await message.answer(
            "❌ Bu telefon raqamli foydalanuvchi topilmadi.\n"
            "Qaytadan kiriting yoki ⬅️ Orqaga bosing."
        )
        return

    enrollments = await get_user_enrollments_with_courses(user['telegram_id'])
    if not enrollments:
        await message.answer(f"⚠️ {user['full_name']} hech qanday kursga yozilmagan.")
        await _go_admin_menu(message, state)
        return

    kicked_from = []
    failed = []
    for e in enrollments:
        group_id = e.get('group_id')
        if not group_id:
            continue
        try:
            await bot.ban_chat_member(chat_id=group_id, user_id=user['telegram_id'])
            await bot.unban_chat_member(chat_id=group_id, user_id=user['telegram_id'])
            kicked_from.append(e['title'])
        except Exception:
            failed.append(e['title'])

    if kicked_from:
        await message.answer(
            f"✅ {user['full_name']} quyidagi guruhlardan chiqarildi:\n"
            + "\n".join(f"• {t}" for t in kicked_from)
        )
    if failed:
        await message.answer(
            f"⚠️ Quyidagi guruhlardan chiqarishda xatolik:\n"
            + "\n".join(f"• {t}" for t in failed)
        )
    if not kicked_from and not failed:
        await message.answer(f"⚠️ {user['full_name']} ning kurslarida guruh ID topilmadi.")

    await _go_admin_menu(message, state)
