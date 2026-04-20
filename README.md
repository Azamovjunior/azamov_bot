# 🤖 A'zamov Academy — Telegram Bot

## Qanday ishlaydi?

```
O'quvchi /start bosadi
       ↓
Platform haqida ma'lumot + Ro'yxatdan o'tish tugmasi
       ↓
Ism, Telefon, Maqsad kiritadi
       ↓
Adminga so'rov keladi [✅ Qabul | ❌ Rad]
       ↓
Admin "Qabul" bosadi → Akk avtomatik yaratiladi
       ↓
O'quvchiga: Login, Parol, App havolasi yuboriladi
       ↓
O'quvchi app ga kiradi! 🎉
```

## O'rnatish

### 1. Bot yaratish
- [@BotFather](https://t.me/BotFather) → `/newbot`
- Token oling

### 2. Admin ID olish
- [@userinfobot](https://t.me/userinfobot) → `/start`
- ID ko'rinadi

### 3. Firebase Admin SDK
- [Firebase Console](https://console.firebase.google.com)
- Project Settings → Service Accounts → **Generate new private key**
- JSON faylni yuklab, `firebase-cred.json` deb saqlang

### 4. Groq API (bepul)
- [console.groq.com](https://console.groq.com) → API Keys

### 5. .env fayl
```bash
cp .env.example .env
# .env faylni tahrirlang
```

### 6. Ishga tushirish
```bash
pip install -r requirements.txt
python bot.py
```

---

## Bot buyruqlari

| Buyruq | Kim | Tavsif |
|--------|-----|--------|
| `/start` | Hammasi | Botni boshlash |
| `/register` | O'quvchi | Ro'yxatdan o'tish |
| `/admin` | Admin | Admin panel |
| `/pending` | Admin | Kutayotgan so'rovlar |
| `/stats` | Admin | Statistika |
| `/stop` | Hammasi | AI chatdan chiqish |
| `/help` | Hammasa | Yordam |

---

## Deployment (Railway.app — bepul)

1. [railway.app](https://railway.app) → GitHub bilan kiring
2. New Project → Deploy from GitHub repo
3. Variables qo'shing (.env dan)
4. `firebase-cred.json` ni ham Variables'ga qo'shing
5. Deploy!
