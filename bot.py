"""
╔══════════════════════════════════════════════════╗
║       A'ZAMOV ACADEMY — TELEGRAM BOT             ║
║  Ro'yxatdan o'tish → Admin tasdiqlash → App kirish║
╚══════════════════════════════════════════════════╝
"""

import asyncio
import logging
import os
import json
import re
import urllib.request
from dotenv import load_dotenv
from groq import Groq

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

import firebase_admin
from firebase_admin import credentials, firestore

# ──────────────────────────────────────
# CONFIG
# ──────────────────────────────────────
load_dotenv()

BOT_TOKEN    = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "YOUR_GROQ_KEY")
ADMIN_IDS    = [int(x) for x in os.getenv("ADMIN_IDS", "123456789").split(",") if x.strip()]
FIREBASE_KEY = os.getenv("FIREBASE_API_KEY", "AIzaSyC1gvNUmUyk4Mt7KfiRyG-A6pU-goDQbEY")
FB_CRED_PATH = os.getenv("FIREBASE_CRED_PATH", "firebase-cred.json")
APP_URL      = os.getenv("APP_URL", "https://azamov-academy.netlify.app")

# Firebase init
cred = credentials.Certificate(FB_CRED_PATH)
firebase_admin.initialize_app(cred)
db = firestore.client()

# Groq init
groq_client = Groq(api_key=GROQ_API_KEY)

# Bot init
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp  = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

# ──────────────────────────────────────
# STATES
# ──────────────────────────────────────
class RegisterState(StatesGroup):
    name  = State()
    phone = State()
    goal  = State()

class AskState(StatesGroup):
    chatting = State()

# ──────────────────────────────────────
# HELPERS
# ──────────────────────────────────────
def is_registered(tg_id: int) -> bool:
    docs = db.collection("registrations").where("telegramId", "==", tg_id).limit(1).stream()
    return any(True for _ in docs)

def get_registration(tg_id: int) -> dict | None:
    docs = list(db.collection("registrations").where("telegramId", "==", tg_id).limit(1).stream())
    if docs:
        return {"id": docs[0].id, **docs[0].to_dict()}
    return None

def create_firebase_user(phone: str, password: str, name: str) -> str | None:
    """Firebase Auth'da user yaratish va UID qaytarish"""
    try:
        email = f"998{phone}@azamovacademy.uz"
        payload = json.dumps({
            "email": email,
            "password": password,
            "returnSecureToken": True
        }).encode()
        req = urllib.request.Request(
            f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_KEY}",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            uid = data.get("localId")

        if uid:
            # Firestore'ga saqlash
            db.collection("users").document(uid).set({
                "name": name,
                "phone": phone,
                "email": email,
                "role": "student",
                "group": "",
                "xp": 0,
                "coins": 0,
                "hearts": 3,
                "streak": 0,
                "status": "active",
                "createdAt": firestore.SERVER_TIMESTAMP
            })
            return uid
    except Exception as e:
        log.error(f"Firebase user create error: {e}")
    return None

# ──────────────────────────────────────
# /START
# ──────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    tg_id = msg.from_user.id

    # Admin tekshirish
    if tg_id in ADMIN_IDS:
        await msg.answer(
            "👑 <b>Admin paneliga xush kelibsiz!</b>\n\n"
            "📋 /pending — Kutayotgan so'rovlar\n"
            "📊 /stats — Statistika\n"
            "📢 /broadcast — Xabar yuborish",
            reply_markup=admin_main_kb()
        )
        return

    # Allaqachon ro'yxatdan o'tganmi?
    reg = get_registration(tg_id)
    if reg:
        status = reg.get("status", "pending")
        if status == "approved":
            await msg.answer(
                f"✅ <b>Siz allaqachon ro'yxatdan o'tgansiz!</b>\n\n"
                f"👤 Ism: <b>{reg.get('name', '—')}</b>\n"
                f"📱 Tel: <b>+998{reg.get('phone', '—')}</b>\n"
                f"🔐 Parol: <code>{reg.get('password', '—')}</code>\n\n"
                f"🌐 App ga kirish: {APP_URL}",
                reply_markup=user_main_kb()
            )
        elif status == "rejected":
            await msg.answer(
                "❌ <b>So'rovingiz rad etilgan.</b>\n\n"
                "Boshqa ma'lumotlar bilan qayta urinib ko'ring yoki admin bilan bog'laning.\n\n"
                "🔄 Qayta ro'yxatdan o'tish uchun /register"
            )
        else:
            await msg.answer(
                "⏳ <b>So'rovingiz admin tomonidan ko'rib chiqilmoqda.</b>\n\n"
                "Tasdiqlangach, login ma'lumotlaringiz yuboriladi. Kuting! 🙏"
            )
        return

    # Yangi foydalanuvchi — xush kelibsiz
    await msg.answer(
        "🎓 <b>A'zamov Academy</b>ga xush kelibsiz!\n\n"
        "📚 O'zbekistonning eng yaxshi online ta'lim platformasi\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "✅ <b>Nima o'rganasiz?</b>\n"
        "🌐 Web dasturlash\n"
        "📱 Mobile dasturlash\n"
        "🤖 AI va Machine Learning\n"
        "🔤 Ingliz tili\n"
        "🎨 Grafik dizayn\n"
        "✈️ Telegram bot\n"
        "➗ Matematika\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🚀 Platformaga kirish uchun ro'yxatdan o'ting!\n"
        "Admin so'rovingizni ko'rib chiqadi va tez orada javob beradi.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✍️ Ro'yxatdan o'tish", callback_data="start_register")],
            [InlineKeyboardButton(text="ℹ️ Platform haqida", callback_data="about")],
            [InlineKeyboardButton(text="🤖 AI bilan gaplash", callback_data="start_ai")],
        ])
    )

# ──────────────────────────────────────
# ABOUT (Platform haqida)
# ──────────────────────────────────────
@router.callback_query(F.data == "about")
async def about_platform(cb: CallbackQuery):
    await cb.message.edit_text(
        "📖 <b>A'zamov Academy haqida</b>\n\n"
        "🏆 <b>Platforma imkoniyatlari:</b>\n"
        "├ 📚 Video darsliklar\n"
        "├ ⚡ Amaliy mashqlar\n"
        "├ 📋 Uyga vazifalar\n"
        "├ 🎯 Test va imtihonlar\n"
        "├ 🏆 Reyting tizimi\n"
        "├ 🪙 Coin va sovrinlar\n"
        "├ 🤖 AI yordamchi\n"
        "└ 📊 Progress kuzatish\n\n"
        "👨‍🏫 <b>Mentor va kuratorlar</b> har bir o'quvchi bilan ishlaydi.\n\n"
        "📱 <b>Qanday ishlaydi?</b>\n"
        "1️⃣ Ro'yxatdan o'ting\n"
        "2️⃣ Admin akk ochib beradi\n"
        "3️⃣ Login va parol yuboriladi\n"
        "4️⃣ App ga kirib, o'rganishni boshlang!\n\n"
        f"🌐 {APP_URL}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✍️ Ro'yxatdan o'tish", callback_data="start_register")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_start")],
        ])
    )
    await cb.answer()

@router.callback_query(F.data == "back_start")
async def back_to_start(cb: CallbackQuery):
    await cb.message.edit_text(
        "🎓 <b>A'zamov Academy</b>ga xush kelibsiz!\n\n"
        "📚 O'zbekistonning eng yaxshi online ta'lim platformasi\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "✅ <b>Nima o'rganasiz?</b>\n"
        "🌐 Web dasturlash\n"
        "📱 Mobile dasturlash\n"
        "🤖 AI va Machine Learning\n"
        "🔤 Ingliz tili\n"
        "🎨 Grafik dizayn\n"
        "✈️ Telegram bot\n"
        "➗ Matematika\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🚀 Platformaga kirish uchun ro'yxatdan o'ting!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✍️ Ro'yxatdan o'tish", callback_data="start_register")],
            [InlineKeyboardButton(text="ℹ️ Platform haqida", callback_data="about")],
            [InlineKeyboardButton(text="🤖 AI bilan gaplash", callback_data="start_ai")],
        ])
    )
    await cb.answer()

# ──────────────────────────────────────
# RO'YXATDAN O'TISH
# ──────────────────────────────────────
@router.callback_query(F.data == "start_register")
async def start_register(cb: CallbackQuery, state: FSMContext):
    tg_id = cb.from_user.id
    if tg_id in ADMIN_IDS:
        await cb.answer("Siz adminsiz!", show_alert=True)
        return

    reg = get_registration(tg_id)
    if reg:
        await cb.answer("Allaqachon ro'yxatdan o'tgansiz!", show_alert=True)
        return

    await cb.message.edit_text(
        "✍️ <b>Ro'yxatdan o'tish</b>\n\n"
        "1️⃣ <b>Ism-Familiyangizni</b> kiriting:\n"
        "<i>Masalan: Ali Valiyev</i>",
    )
    await state.set_state(RegisterState.name)
    await cb.answer()

@router.message(RegisterState.name)
async def reg_name(msg: Message, state: FSMContext):
    name = (msg.text or "").strip()
    if len(name) < 3:
        await msg.answer("❌ Ism kamida 3 belgi bo'lishi kerak. Qayta kiriting:")
        return
    if len(name) > 60:
        await msg.answer("❌ Ism juda uzun. Qayta kiriting:")
        return

    await state.update_data(name=name)
    await msg.answer(
        f"✅ Ism: <b>{name}</b>\n\n"
        "2️⃣ <b>Telefon raqamingizni</b> kiriting:\n"
        "<i>Faqat raqamlar, masalan: 901234567</i>",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📱 Raqamni yuborish", request_contact=True)]],
            resize_keyboard=True, one_time_keyboard=True
        )
    )
    await state.set_state(RegisterState.phone)

@router.message(RegisterState.phone)
async def reg_phone(msg: Message, state: FSMContext):
    # Contact orqali yoki matn orqali
    if msg.contact:
        phone = re.sub(r"\D", "", msg.contact.phone_number)
        if phone.startswith("998"):
            phone = phone[3:]
    else:
        phone = re.sub(r"\D", "", msg.text or "")
        if phone.startswith("998"):
            phone = phone[3:]

    if len(phone) != 9:
        await msg.answer(
            "❌ Telefon noto'g'ri! 9 ta raqam kiriting:\n"
            "<i>Masalan: 901234567</i>",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    await state.update_data(phone=phone)
    await msg.answer(
        f"✅ Tel: <b>+998{phone}</b>\n\n"
        "3️⃣ <b>Nima o'rganmoqchisiz?</b>\n"
        "Quyidagidan tanlang yoki o'zingiz yozing:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🌐 Web dasturlash"), KeyboardButton(text="📱 Mobile")],
                [KeyboardButton(text="🤖 AI / ML"), KeyboardButton(text="🔤 Ingliz tili")],
                [KeyboardButton(text="🎨 Grafik dizayn"), KeyboardButton(text="✈️ Telegram bot")],
                [KeyboardButton(text="➗ Matematika"), KeyboardButton(text="💻 Barchasi")],
            ],
            resize_keyboard=True, one_time_keyboard=True
        )
    )
    await state.set_state(RegisterState.goal)

@router.message(RegisterState.goal)
async def reg_goal(msg: Message, state: FSMContext):
    goal = (msg.text or "").strip()
    if not goal:
        await msg.answer("❌ Maqsadingizni kiriting:")
        return

    data = await state.get_data()
    name = data["name"]
    phone = data["phone"]

    # Firestore'ga so'rov saqlash
    await state.clear()

    doc_ref = db.collection("registrations").add({
        "telegramId": msg.from_user.id,
        "telegramUsername": msg.from_user.username or "",
        "name": name,
        "phone": phone,
        "goal": goal,
        "status": "pending",
        "createdAt": firestore.SERVER_TIMESTAMP
    })

    # Foydalanuvchiga tasdiqlash xabari
    await msg.answer(
        "🎉 <b>So'rovingiz muvaffaqiyatli yuborildi!</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Ism: <b>{name}</b>\n"
        f"📱 Tel: <b>+998{phone}</b>\n"
        f"🎯 Maqsad: <b>{goal}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        "⏳ Admin ko'rib chiqadi va tez orada:\n"
        "✅ Login\n"
        "✅ Parol\n"
        "✅ App havolasi\n"
        "...yuboriladi!\n\n"
        "🙏 Sabr qiling, odatda 1-24 soat ichida javob beriladi.",
        reply_markup=ReplyKeyboardRemove()
    )

    await msg.answer(
        "Attendayotgan vaqtda platform haqida ko'proq bilib oling 👇",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="ℹ️ Platform haqida", callback_data="about")],
            [InlineKeyboardButton(text="🤖 AI bilan gaplash", callback_data="start_ai")],
        ])
    )

    # Adminga xabar
    reg_id = doc_ref[1].id
    admin_text = (
        f"🆕 <b>Yangi ro'yxatdan o'tish so'rovi!</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Ism: <b>{name}</b>\n"
        f"📱 Tel: <b>+998{phone}</b>\n"
        f"🎯 Maqsad: <b>{goal}</b>\n"
        f"💬 TG: @{msg.from_user.username or '—'}\n"
        f"🆔 TG ID: <code>{msg.from_user.id}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )

    approve_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Qabul qilish", callback_data=f"approve:{reg_id}:{msg.from_user.id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject:{reg_id}:{msg.from_user.id}"),
        ]
    ])

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_text, reply_markup=approve_kb)
        except Exception as e:
            log.error(f"Admin notify error: {e}")

# ──────────────────────────────────────
# ADMIN — QABUL QILISH / RAD ETISH
# ──────────────────────────────────────
@router.callback_query(F.data.startswith("approve:"))
async def admin_approve(cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    parts = cb.data.split(":")
    reg_id = parts[1]
    user_tg_id = int(parts[2])

    # Ro'yxatdan ma'lumot olish
    reg_doc = db.collection("registrations").document(reg_id).get()
    if not reg_doc.exists:
        await cb.answer("So'rov topilmadi!", show_alert=True)
        return

    reg = reg_doc.to_dict()
    if reg.get("status") != "pending":
        await cb.answer("Bu so'rov allaqachon ko'rib chiqilgan!", show_alert=True)
        return

    name  = reg["name"]
    phone = reg["phone"]

    # Parol yaratish (telefon oxirgi 4 raqami + ism bosh harfi)
    password = f"Az{phone[-4:]}@{name[0].upper()}"

    proc_msg = await cb.message.edit_text(
        cb.message.text + "\n\n⏳ <b>Akk yaratilmoqda...</b>"
    )

    # Firebase Auth + Firestore user yaratish
    uid = create_firebase_user(phone, password, name)

    if not uid:
        await proc_msg.edit_text(
            cb.message.text + "\n\n❌ <b>Firebase xatolik!</b> Qayta urinib ko'ring."
        )
        await cb.answer("❌ Xatolik yuz berdi", show_alert=True)
        return

    # Registration statusini yangilash
    db.collection("registrations").document(reg_id).update({
        "status": "approved",
        "uid": uid,
        "password": password,
        "approvedAt": firestore.SERVER_TIMESTAMP,
        "approvedBy": cb.from_user.id
    })

    # Admin xabari yangilansin
    await proc_msg.edit_text(
        cb.message.text.replace("⏳ Akk yaratilmoqda...", "").strip() +
        f"\n\n✅ <b>QABUL QILINDI</b>\n"
        f"🔐 Parol: <code>{password}</code>\n"
        f"🆔 UID: <code>{uid}</code>"
    )

    # Foydalanuvchiga xabar yuborish
    try:
        await bot.send_message(
            user_tg_id,
            f"🎉 <b>Tabriklaymiz, {name}!</b>\n\n"
            f"✅ So'rovingiz <b>qabul qilindi!</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🌐 <b>App havolasi:</b>\n"
            f"{APP_URL}\n\n"
            f"📱 <b>Login ma'lumotlari:</b>\n"
            f"📞 Telefon: <code>+998{phone}</code>\n"
            f"🔐 Parol: <code>{password}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>Qanday kirish:</b>\n"
            f"1️⃣ Havolani oching: {APP_URL}\n"
            f"2️⃣ Telefon: <code>{phone}</code>\n"
            f"3️⃣ Parol: <code>{password}</code>\n"
            f"4️⃣ 'Kirish' tugmasini bosing!\n\n"
            f"⚠️ Parolni o'zgartirishni unutmang!\n\n"
            f"🚀 O'rganishni boshlang va oldinga boring! 💪",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🌐 App ga kirish", url=APP_URL)],
                [InlineKeyboardButton(text="ℹ️ Yordam", callback_data="help_user")],
            ])
        )
        await cb.answer("✅ Qabul qilindi va foydalanuvchiga xabar yuborildi!")
    except Exception as e:
        await cb.answer(f"⚠️ Xabar yuborilmadi: {e}", show_alert=True)


@router.callback_query(F.data.startswith("reject:"))
async def admin_reject(cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    parts = cb.data.split(":")
    reg_id = parts[1]
    user_tg_id = int(parts[2])

    reg_doc = db.collection("registrations").document(reg_id).get()
    if not reg_doc.exists:
        await cb.answer("So'rov topilmadi!", show_alert=True)
        return

    reg = reg_doc.to_dict()
    if reg.get("status") != "pending":
        await cb.answer("Allaqachon ko'rib chiqilgan!", show_alert=True)
        return

    # Statusni yangilash
    db.collection("registrations").document(reg_id).update({
        "status": "rejected",
        "rejectedAt": firestore.SERVER_TIMESTAMP,
        "rejectedBy": cb.from_user.id
    })

    await cb.message.edit_text(
        cb.message.text + "\n\n❌ <b>RAD ETILDI</b>"
    )

    # Foydalanuvchiga xabar
    try:
        await bot.send_message(
            user_tg_id,
            f"😔 <b>Afsuski, so'rovingiz rad etildi.</b>\n\n"
            f"Sabab haqida ko'proq ma'lumot olish uchun admin bilan bog'laning.\n\n"
            f"🔄 Boshqa ma'lumotlar bilan qayta urinib ko'ring: /start",
        )
        await cb.answer("❌ Rad etildi")
    except Exception as e:
        await cb.answer(f"Xabar yuborilmadi: {e}", show_alert=True)

# ──────────────────────────────────────
# USER — O'Z MA'LUMOTLARINI KO'RISH
# ──────────────────────────────────────
def user_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 App ga kirish", url=APP_URL)],
        [InlineKeyboardButton(text="📋 Ma'lumotlarim", callback_data="my_info")],
        [InlineKeyboardButton(text="🤖 AI bilan gaplash", callback_data="start_ai")],
        [InlineKeyboardButton(text="ℹ️ Yordam", callback_data="help_user")],
    ])

@router.callback_query(F.data == "my_info")
async def user_info(cb: CallbackQuery):
    tg_id = cb.from_user.id
    reg = get_registration(tg_id)
    if not reg or reg.get("status") != "approved":
        await cb.answer("Ma'lumot topilmadi", show_alert=True)
        return

    await cb.message.edit_text(
        f"📋 <b>Mening ma'lumotlarim</b>\n\n"
        f"👤 Ism: <b>{reg.get('name', '—')}</b>\n"
        f"📱 Tel: <b>+998{reg.get('phone', '—')}</b>\n"
        f"🔐 Parol: <code>{reg.get('password', '—')}</code>\n\n"
        f"🌐 App: {APP_URL}\n\n"
        f"⚠️ Parolni hech kimga bermang!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌐 App ga kirish", url=APP_URL)],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_approved")],
        ])
    )
    await cb.answer()

@router.callback_query(F.data == "back_approved")
async def back_approved(cb: CallbackQuery):
    reg = get_registration(cb.from_user.id)
    name = reg.get("name", "Foydalanuvchi") if reg else "Foydalanuvchi"
    await cb.message.edit_text(
        f"✅ <b>Xush kelibsiz, {name}!</b>\n\n"
        f"Quyida ilovamizga kirishingiz mumkin:",
        reply_markup=user_main_kb()
    )
    await cb.answer()

@router.callback_query(F.data == "help_user")
async def help_user(cb: CallbackQuery):
    await cb.message.edit_text(
        "❓ <b>Yordam</b>\n\n"
        "🔐 <b>Parolni unutdim:</b>\n"
        "   Admin bilan bog'laning\n\n"
        "📱 <b>Telefon raqamim o'zgardi:</b>\n"
        "   Admin bilan bog'laning\n\n"
        "📚 <b>Kurs ko'rinmayapti:</b>\n"
        "   Admin tayinlaydi, biroz kuting\n\n"
        "🐛 <b>Xatolik bor:</b>\n"
        "   /feedback buyrug'ini ishlating\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "📩 Admin: @azamovacademy",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_approved")],
        ])
    )
    await cb.answer()

# ──────────────────────────────────────
# GROQ AI CHAT
# ──────────────────────────────────────
SYSTEM_AI = """Sen "A'zamov Academy" platformasining AI yordamchisisna. Sening isming "A'zamov AI".
Foydalanuvchilarga platforma haqida, kurslar haqida va dasturlash bo'yicha yordam berasan.
Har doim O'zbek tilida, qisqa va foydali javob ber.
Hech qachon o'zingni "Groq" yoki "LLaMA" deb tanishtirma."""

ai_history: dict[int, list] = {}

@router.callback_query(F.data == "start_ai")
async def ai_cb_start(cb: CallbackQuery, state: FSMContext):
    ai_history[cb.from_user.id] = []
    await cb.message.edit_text(
        "🤖 <b>A'zamov AI</b> — Sizning yordamchingiz!\n\n"
        "💬 Savol bering — javob beraman.\n"
        "📚 Dasturlash, ingliz tili, matematika...\n\n"
        "✉️ Xabaringizni yozing!\n"
        "🛑 Chiqish: /stop"
    )
    await state.set_state(AskState.chatting)
    await cb.answer()

@router.message(F.text == "🤖 AI bilan gaplash")
async def ai_text_start(msg: Message, state: FSMContext):
    ai_history[msg.from_user.id] = []
    await msg.answer(
        "🤖 <b>A'zamov AI</b> — Sizning yordamchingiz!\n\n"
        "💬 Savol bering!\n"
        "🛑 Chiqish: /stop",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🛑 Chiqish")]],
            resize_keyboard=True
        )
    )
    await state.set_state(AskState.chatting)

@router.message(AskState.chatting, F.text.in_(["🛑 Chiqish", "/stop"]))
async def ai_stop(msg: Message, state: FSMContext):
    ai_history.pop(msg.from_user.id, None)
    await state.clear()
    tg_id = msg.from_user.id
    reg = get_registration(tg_id)
    status = reg.get("status") if reg else None

    if status == "approved":
        await msg.answer("✅ AI chatdan chiqildi.", reply_markup=ReplyKeyboardRemove())
        await msg.answer("Bosh menyu:", reply_markup=user_main_kb())
    else:
        await msg.answer(
            "✅ AI chatdan chiqildi.",
            reply_markup=ReplyKeyboardRemove()
        )
        await msg.answer(
            "Nima qilishingiz mumkin:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✍️ Ro'yxatdan o'tish", callback_data="start_register")],
                [InlineKeyboardButton(text="ℹ️ Platform haqida", callback_data="about")],
            ])
        )

@router.message(AskState.chatting)
async def ai_reply(msg: Message, state: FSMContext):
    if not msg.text:
        await msg.answer("Faqat matn yuboring 📝")
        return

    tg_id = msg.from_user.id
    if tg_id not in ai_history:
        ai_history[tg_id] = []

    typing = await msg.answer("🤖 <i>Javob yozmoqda...</i>")
    ai_history[tg_id].append({"role": "user", "content": msg.text})

    # Keep last 10 messages only
    if len(ai_history[tg_id]) > 20:
        ai_history[tg_id] = ai_history[tg_id][-20:]

    try:
        resp = groq_client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "system", "content": SYSTEM_AI}] + ai_history[tg_id],
            max_tokens=700,
            temperature=0.7
        )
        answer = resp.choices[0].message.content
        ai_history[tg_id].append({"role": "assistant", "content": answer})

        await typing.delete()
        # Long message split
        if len(answer) > 4000:
            for chunk in [answer[i:i+4000] for i in range(0, len(answer), 4000)]:
                await msg.answer(chunk)
        else:
            await msg.answer(answer)

    except Exception as e:
        await typing.delete()
        await msg.answer(f"❌ Xatolik yuz berdi. Qayta urinib ko'ring.\n<i>{e}</i>")

# ──────────────────────────────────────
# ADMIN PANEL
# ──────────────────────────────────────
def admin_main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 So'rovlar"), KeyboardButton(text="📊 Statistika")],
            [KeyboardButton(text="📢 Xabar yuborish"), KeyboardButton(text="👥 Foydalanuvchilar")],
        ],
        resize_keyboard=True
    )

@router.message(Command("admin"))
async def admin_panel(msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        await msg.answer("❌ Ruxsat yo'q!")
        return
    await msg.answer("👑 <b>Admin panel</b>", reply_markup=admin_main_kb())

@router.message(F.text == "📋 So'rovlar")
async def pending_list(msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return

    pending = list(
        db.collection("registrations")
        .where("status", "==", "pending")
        .order_by("createdAt", direction=firestore.Query.DESCENDING)
        .limit(10).stream()
    )

    if not pending:
        await msg.answer("✅ Kutayotgan so'rov yo'q!")
        return

    await msg.answer(f"📋 <b>Kutayotgan so'rovlar: {len(pending)} ta</b>")

    for doc in pending:
        d = doc.to_dict()
        approve_kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Qabul", callback_data=f"approve:{doc.id}:{d.get('telegramId', 0)}"),
                InlineKeyboardButton(text="❌ Rad", callback_data=f"reject:{doc.id}:{d.get('telegramId', 0)}"),
            ]
        ])
        await msg.answer(
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>{d.get('name', '—')}</b>\n"
            f"📱 +998{d.get('phone', '—')}\n"
            f"🎯 {d.get('goal', '—')}\n"
            f"💬 @{d.get('telegramUsername', '—')}",
            reply_markup=approve_kb
        )

@router.message(Command("pending"))
async def cmd_pending(msg: Message):
    await pending_list(msg)

@router.message(F.text == "📊 Statistika")
async def admin_stats(msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return

    try:
        total  = len(list(db.collection("registrations").stream()))
        approved = len(list(db.collection("registrations").where("status", "==", "approved").stream()))
        pending  = len(list(db.collection("registrations").where("status", "==", "pending").stream()))
        rejected = len(list(db.collection("registrations").where("status", "==", "rejected").stream()))
        users    = len(list(db.collection("users").where("role", "==", "student").stream()))

        await msg.answer(
            f"📊 <b>Statistika</b>\n\n"
            f"📋 Jami so'rovlar: <b>{total}</b>\n"
            f"✅ Qabul qilingan: <b>{approved}</b>\n"
            f"⏳ Kutayotgan: <b>{pending}</b>\n"
            f"❌ Rad etilgan: <b>{rejected}</b>\n\n"
            f"👥 Platformadagi o'quvchilar: <b>{users}</b>"
        )
    except Exception as e:
        await msg.answer(f"❌ Xatolik: {e}")

@router.message(Command("stats"))
async def cmd_stats(msg: Message):
    await admin_stats(msg)

@router.message(F.text == "📢 Xabar yuborish")
async def broadcast_start(msg: Message, state: FSMContext):
    if msg.from_user.id not in ADMIN_IDS:
        return
    await msg.answer(
        "📢 <b>Barcha ro'yxatdan o'tganlarga xabar</b>\n\n"
        "Xabar matnini kiriting:\n"
        "<i>Bekor: /stop</i>",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Bekor")]],
            resize_keyboard=True
        )
    )
    await state.set_state(AskState.chatting)
    await state.update_data(broadcast_mode=True)

@router.message(F.text == "👥 Foydalanuvchilar")
async def user_list(msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return

    docs = list(
        db.collection("registrations")
        .where("status", "==", "approved")
        .order_by("createdAt", direction=firestore.Query.DESCENDING)
        .limit(20).stream()
    )

    if not docs:
        await msg.answer("👥 Hali qabul qilingan foydalanuvchi yo'q")
        return

    text = f"👥 <b>Qabul qilinganlar ({len(docs)} ta):</b>\n\n"
    for d in docs:
        dd = d.to_dict()
        text += f"✅ <b>{dd.get('name', '—')}</b> · +998{dd.get('phone', '—')}\n"

    await msg.answer(text)

# ──────────────────────────────────────
# /REGISTER COMMAND
# ──────────────────────────────────────
@router.message(Command("register"))
async def cmd_register(msg: Message, state: FSMContext):
    tg_id = msg.from_user.id
    if tg_id in ADMIN_IDS:
        await msg.answer("Siz adminsiz!")
        return

    reg = get_registration(tg_id)
    if reg and reg.get("status") == "approved":
        await msg.answer("✅ Allaqachon ro'yxatdan o'tgansiz va qabul qilingansiz!")
        return

    await state.clear()
    await msg.answer(
        "✍️ <b>Ro'yxatdan o'tish</b>\n\n"
        "1️⃣ <b>Ism-Familiyangizni</b> kiriting:"
    )
    await state.set_state(RegisterState.name)

# ──────────────────────────────────────
# /FEEDBACK
# ──────────────────────────────────────
@router.message(Command("feedback"))
async def cmd_feedback(msg: Message):
    await msg.answer(
        "📩 <b>Muammo yoki taklif bormi?</b>\n\n"
        "Quyidagi matnni yozing:\n"
        "<code>/feedback [xabaringiz]</code>\n\n"
        "Yoki admin bilan to'g'ridan-to'g'ri bog'laning: @azamovacademy"
    )

# ──────────────────────────────────────
# HELP
# ──────────────────────────────────────
@router.message(Command("help"))
async def cmd_help(msg: Message):
    tg_id = msg.from_user.id
    is_admin_user = tg_id in ADMIN_IDS
    reg = get_registration(tg_id)

    if is_admin_user:
        text = (
            "👑 <b>Admin buyruqlari:</b>\n\n"
            "/pending — So'rovlar ro'yxati\n"
            "/stats — Statistika\n"
            "/admin — Admin menyu\n"
        )
    elif reg and reg.get("status") == "approved":
        text = (
            "❓ <b>Yordam</b>\n\n"
            "/start — Bosh menyu\n"
            f"🌐 App: {APP_URL}\n\n"
            "📩 Admin: @azamovacademy"
        )
    else:
        text = (
            "❓ <b>Yordam</b>\n\n"
            "/start — Botni boshlash\n"
            "/register — Ro'yxatdan o'tish\n\n"
            "📩 Admin: @azamovacademy"
        )

    await msg.answer(text)

# ──────────────────────────────────────
# UNKNOWN
# ──────────────────────────────────────
@router.message()
async def unknown(msg: Message, state: FSMContext):
    cur = await state.get_state()
    if cur:
        return

    tg_id = msg.from_user.id
    if tg_id in ADMIN_IDS:
        await msg.answer("❓ Buyruq topilmadi. /help", reply_markup=admin_main_kb())
        return

    reg = get_registration(tg_id)
    if reg and reg.get("status") == "approved":
        await msg.answer(
            "❓ Buyruq topilmadi.",
            reply_markup=user_main_kb()
        )
    else:
        await msg.answer(
            "❓ /start buyrug'ini bosing.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Boshiga qaytish", callback_data="back_start")]
            ])
        )

# ──────────────────────────────────────
# MAIN
# ──────────────────────────────────────
async def main():
    log.info("🚀 A'zamov Academy Bot ishga tushmoqda...")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
