import asyncio
import logging
import os
from flask import Flask
from threading import Thread

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN
from handlers import start, media

# Logging sozlamalari
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# --- VEB SERVER QISMI (UptimeRobot uchun) ---
app = Flask('')

@app.route('/')
def home():
    return "✅ Bot is running and alive!"

def run_web_server():
    # Render o'zi avtomatik PORT beradi, agar topilmasa 8080 ishlatiladi
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    # Veb-serverni alohida oqimda (thread) ishga tushiramiz
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()
# --------------------------------------------

async def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN .env faylida ko'rsatilmagan!")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Routerlarni ulash
    dp.include_router(start.router)
    dp.include_router(media.router)

    # Veb-serverni uyg'otish
    print("🌐 Veb-server ishga tushmoqda...")
    keep_alive()

    print("🚀 Bot polling rejimida ishga tushdi!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi!")