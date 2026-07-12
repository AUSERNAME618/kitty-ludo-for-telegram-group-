# راه‌اندازی بات منچ (Mench) از صفر

## قدم ۱ — ساخت بات تو تلگرام
1. تو تلگرام برو سراغ `@BotFather`
2. بزن `/newbot`
3. یه اسم بده (مثلاً `Mench Game`) و یه یوزرنیم که به `bot` ختم بشه
4. توکن رو نگه دار (شبیه `123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)
5. حتماً بزن `/setinline` و بات‌تو انتخاب کن — وگرنه تگ‌کردن با فاصله کار نمی‌کنه

## قدم ۲ — آماده‌سازی
```bash
python3 --version   # باید 3.10+ باشه
pip install python-telegram-bot --upgrade
pip install Pillow
```

## قدم ۳ — فایل‌ها
همه‌ی این‌ها رو تو یه پوشه بذار (ساختار پوشه دقیقاً همینه):
```
mench_bot.py
persistence.py
render_helper.py
render_board_custom.py
board_geometry.py
game_engine.py
board_safe.jpg
board_normal.jpg
pieces/sized/*.png   (۲۰ فایل: ۴ رنگ × ۵ سایز)
```

## قدم ۴ — اجرا
```bash
export BOT_TOKEN="توکنت"
python3 mench_bot.py
```
تو گروه: بات رو اضافه کن (ادمین یا privacy mode خاموش)، `@یوزرنیم_باتت` + فاصله بزن، یه حالت انتخاب کن، بقیه «بزن بریم» بزنن، بعد «شروع بازی».

## وضعیت فعلی — نهایی شده
- تخته: عکس واقعی خودت (گربه‌ای)، دو نسخه‌ی سیف/نرمال، خودکار بر اساس حالت بازی انتخاب می‌شه
- مهره‌ها: عکس ۴ گربه (مشکی/سفید/نارنجی/سه‌رنگ)، جای دقیقشون تو لونه‌ها و مسیر کالیبره شده
- موتور بازی: تاس، نوبت، سیف‌مود، برد سریع/کامل — همه تست‌شده

## مرحله‌ی بعدی — هاست روی Render + Neon

### دیتابیس (Neon)
1. تو [neon.tech](https://neon.tech) یه پروژه‌ی رایگان بساز
2. یه Connection String می‌ده شبیه: `postgres://user:pass@host/dbname?sslmode=require`
3. این رو به‌عنوان env var بذار: `DATABASE_URL`

### بات (Render)
1. کد رو تو یه ریپازیتوری گیت‌هاب بذار (شامل همه‌ی فایل‌های بالا + `requirements.txt`)
2. تو Render یه **Web Service** بساز (نه Background Worker — چون برای اینکه UptimeRobot بتونه پینگش کنه، بات به یه URL عمومی نیاز داره؛ حالا بات هم پولینگ تلگرام رو انجام می‌ده هم یه health-check endpoint سبک داره)
3. Environment Variables: `BOT_TOKEN` و `DATABASE_URL` رو ست کن (`PORT` رو خودِ Render خودکار می‌ده، کاری باهاش نداشته باش)
4. Start Command: `python3 mench_bot.py`
5. بعد از دیپلوی، Render یه آدرس می‌ده شبیه `https://your-app.onrender.com` — این همون آدرسیه که تو UptimeRobot می‌ذاری

### requirements.txt
```
python-telegram-bot
Pillow
psycopg2-binary
aiohttp
```

### UptimeRobot
یه Monitor جدید بساز، نوع HTTP(s)، آدرس رو بذار `https://your-app.onrender.com/health`، فاصله‌ی پینگ رو کمتر از ۱۵ دقیقه بذار (همون آستانه‌ی خواب‌رفتن Render رایگان).


