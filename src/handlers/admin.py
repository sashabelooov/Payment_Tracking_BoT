import os
import tempfile
from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.types import Message, ReplyKeyboardRemove, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command

from states import AdminState, UserState
import keyboards as kb
from config import ADMIN_IDS, GROUP_ID
from database.queries import (
    get_all_users, get_payment_stats, deactivate_user,
    create_course, get_all_courses, get_course,
    get_course_enrollments_with_users, update_user_language,
)

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.message(Command("admin"))
async def admin_command(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(
        text="🔧 Admin panel",
        reply_markup=kb.admin_menu(),
    )
    await state.set_state(AdminState.menu)


@router.message(AdminState.menu)
async def admin_menu_handler(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
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

        # Telegram message limit is 4096 chars
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

    elif message.text == "⬅️ Chiqish":
        await state.clear()
        await message.answer(
            "Admin paneldan chiqildi.",
            reply_markup=ReplyKeyboardRemove(),
        )


@router.message(AdminState.broadcast)
async def broadcast_handler(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    if message.text == "⬅️ Orqaga":
        await message.answer("🔧 Admin panel", reply_markup=kb.admin_menu())
        await state.set_state(AdminState.menu)
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
        reply_markup=kb.admin_menu(),
    )
    await state.set_state(AdminState.menu)


# --- Course creation FSM ---

@router.message(AdminState.course_title)
async def course_title_handler(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if message.text == "⬅️ Orqaga":
        await message.answer("🔧 Admin panel", reply_markup=kb.admin_menu())
        await state.set_state(AdminState.menu)
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
    if not is_admin(message.from_user.id):
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
    if not is_admin(message.from_user.id):
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
    if not is_admin(message.from_user.id):
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
    if not is_admin(message.from_user.id):
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
    if not is_admin(message.from_user.id):
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
    if not is_admin(message.from_user.id):
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
    if not is_admin(message.from_user.id):
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
    await message.answer(text, reply_markup=kb.conf("🇺🇿 uz"))
    await state.set_state(AdminState.course_confirm)


@router.message(AdminState.course_confirm)
async def course_confirm_handler(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
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
        await message.answer(
            "✅ Kurs muvaffaqiyatli yaratildi!",
            reply_markup=kb.admin_menu(),
        )
        await state.set_state(AdminState.menu)

    elif message.text == "❌ Bekor qilish":
        await message.answer(
            "Kurs yaratish bekor qilindi.",
            reply_markup=kb.admin_menu(),
        )
        await state.set_state(AdminState.menu)


# --- Excel export ---

@router.message(AdminState.export_select_course)
async def export_course_handler(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return

    if message.text == "⬅️ Orqaga":
        await message.answer("🔧 Admin panel", reply_markup=kb.admin_menu())
        await state.set_state(AdminState.menu)
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

    await message.answer("🔧 Admin panel", reply_markup=kb.admin_menu())
    await state.set_state(AdminState.menu)


# --- Admin language change ---

@router.message(AdminState.change_language)
async def admin_change_language_handler(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
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

    await message.answer("🔧 Admin panel", reply_markup=kb.admin_menu())
    await state.set_state(AdminState.menu)
