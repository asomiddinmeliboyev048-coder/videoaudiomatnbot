import asyncio
import logging
import os
from aiogram import Router, Bot, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    FSInputFile
)

# Groq kutubxonasi
from groq import Groq

from config import BOT_TOKEN, GROQ_API_KEY
from handlers.subscription import check_subscription
from handlers.start import get_subscribe_keyboard
from services.transcribe import process_audio
from services.extract_audio import extract_audio_from_video
from services.ocr import extract_text_from_image
from utils.helpers import get_temp_path, cleanup_file

logger = logging.getLogger(__name__)
router = Router()

# Groq mijozini sozlash
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

file_store: dict = {}
counter = 0

# --- YORDAMCHI AI FUNKSIYASI ---
async def get_ai_answer(question_text: str) -> str:
    """Groq AI dan javob olish uchun umumiy funksiya"""
    try:
        if not groq_client:
            return "⚠️ API kalit sozlanmagan."
        
        loop = asyncio.get_event_loop()
        # Bloklanib qolmaslik uchun executor ishlatamiz
        completion = await loop.run_in_executor(None, lambda: groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Siz aqlli yordamchisiz. Savollarga faqat o'zbek tilida, aniq va imloviy xatosiz javob bering."},
                {"role": "user", "content": question_text}
            ],
            temperature=0.6,
            max_tokens=1500
        ))
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return "Kechirasiz, savolingizni tahlil qilishda xatolik yuz berdi."

def save_file_id(file_id: str) -> str:
    global counter
    counter += 1
    key = str(counter)
    file_store[key] = file_id
    return key

def get_file_id(key: str) -> str:
    return file_store.get(key, "")

def get_video_keyboard(key: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Matnni olish", callback_data=f"vt:{key}"),
            InlineKeyboardButton(text="🎵 Audioni olish", callback_data=f"va:{key}")
        ]
    ])

async def send_long_text(message: Message, text: str, chunk_size: int = 4000):
    for i in range(0, len(text), chunk_size):
        await message.answer(text[i:i + chunk_size])

# ─── MATNLI SAVOL (AI) ────────────────────────────────────────────────────────

@router.message(F.text & ~F.text.startswith('/'))
async def handle_ai_question(message: Message, bot: Bot):
    if not await check_subscription(bot, message.from_user.id):
        await message.answer("🔒 Avval kanalga a'zo bo'ling:", reply_markup=get_subscribe_keyboard())
        return

    processing = await message.answer("🤔 O'ylayapman...")
    answer = await get_ai_answer(message.text)
    
    await processing.delete()
    await message.answer(answer, parse_mode="Markdown")

# ─── OVOZLI XABAR SAVOLI (AI) ──────────────────────────────────────────────────

@router.message(F.voice)
async def handle_voice(message: Message, bot: Bot):
    if not await check_subscription(bot, message.from_user.id):
        await message.answer("🔒 Avval kanalga a'zo bo'ling:", reply_markup=get_subscribe_keyboard())
        return

    processing = await message.answer("🎤 Ovozli xabar eshitilmoqda...")
    audio_path = get_temp_path("ogg")

    try:
        file = await bot.get_file(message.voice.file_id)
        await bot.download_file(file.file_path, destination=audio_path)
        
        # 1. Ovozni matnga o'giramiz
        transcript = await process_audio(audio_path)
        
        if not transcript or len(transcript.strip()) < 2:
            await processing.edit_text("⚠️ Ovozli xabarni tushuna olmadim.")
            return

        # 2. Foydalanuvchiga nima tushunilganini ko'rsatamiz
        await processing.edit_text(f"📝 **Sizning savolingiz:**\n_{transcript}_\n\n⌛ **Javob tayyorlanmoqda...**", parse_mode="Markdown")
        
        # 3. Matnni AI'ga yuboramiz
        ai_answer = await get_ai_answer(transcript)
        
        # 4. Yakuniy javob
        await message.answer(f"🤖 **AI javobi:**\n\n{ai_answer}", parse_mode="Markdown")
        await processing.delete()

    except Exception as e:
        logger.error(f"Voice AI Error: {e}")
        await processing.edit_text("❌ Ovozli xabarni ishlashda xatolik yuz berdi.")
    finally:
        cleanup_file(audio_path)

# ─── VIDEO ────────────────────────────────────────────────────────────────────

@router.message(F.video)
async def handle_video(message: Message, bot: Bot):
    if not await check_subscription(bot, message.from_user.id):
        await message.answer("🔒 Avval kanalga a'zo bo'ling:", reply_markup=get_subscribe_keyboard())
        return

    size_mb = (message.video.file_size or 0) / (1024 * 1024)
    if size_mb > 50:
        await message.answer(f"❌ Fayl juda katta ({size_mb:.1f} MB). Maksimum: 50 MB.")
        return

    key = save_file_id(message.video.file_id)
    await message.answer("🎬 Video qabul qilindi! Nima qilishni tanlang:", reply_markup=get_video_keyboard(key))

# ─── CALLBACKLAR (VIDEO MATNI UCHUN) ──────────────────────────────────────────

@router.callback_query(lambda c: c.data and c.data.startswith("vt:"))
async def get_text_callback(callback: CallbackQuery, bot: Bot):
    key = callback.data[3:]
    file_id = get_file_id(key)
    await callback.answer()

    if not file_id:
        await callback.message.answer("❌ Video topilmadi.")
        return

    processing = await callback.message.answer("⏳ Audio matnga aylantirilmoqda (O'zbek tili ustuvor)...")
    video_path = get_temp_path("mp4")
    audio_path = get_temp_path("mp3")

    try:
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, destination=video_path)
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, extract_audio_from_video, video_path, audio_path)
        
        text = await process_audio(audio_path)
        await processing.delete()

        if not text:
            await callback.message.answer("⚠️ Videoda nutq aniqlanmadi.")
        else:
            await callback.message.answer("✅ **Video matni:**", parse_mode="Markdown")
            await send_long_text(callback.message, text)
    except Exception as e:
        await processing.edit_text(f"❌ Xatolik: {str(e)}")
    finally:
        cleanup_file(video_path)
        cleanup_file(audio_path)

# ─── RASM (PHOTO) ─────────────────────────────────────────────────────────────

@router.message(F.photo)
async def handle_photo(message: Message, bot: Bot):
    if not await check_subscription(bot, message.from_user.id):
        await message.answer("🔒 Avval kanalga a'zo bo'ling:", reply_markup=get_subscribe_keyboard())
        return

    processing = await message.answer("🔍 Rasmdagi matn o'qilmoqda...")
    image_path = get_temp_path("jpg")

    try:
        # Eng yuqori sifatli rasmni yuklab olish
        file = await bot.get_file(message.photo[-1].file_id)
        await bot.download_file(file.file_path, destination=image_path)
        
        # OCR xizmatini asinxron ishlatish
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, extract_text_from_image, image_path)

        await processing.delete()

        if not text or not text.strip():
            await message.answer("⚠️ Rasmdan hech qanday matn topilmadi.")
        else:
            await message.answer("✅ **Rasmdan aniqlangan matn:**")
            await send_long_text(message, text)

    except Exception as e:
        logger.error(f"OCR Error: {e}")
        await processing.edit_text(f"❌ Rasmni tahlil qilishda xatolik yuz berdi.")
    finally:
        cleanup_file(image_path)

# ─── CALLBACKLAR (VIDEO AUDIOSI UCHUN) ────────────────────────────────────────

@router.callback_query(lambda c: c.data and c.data.startswith("va:"))
async def get_audio_callback(callback: CallbackQuery, bot: Bot):
    key = callback.data[3:]
    file_id = get_file_id(key)
    await callback.answer()

    if not file_id:
        await callback.message.answer("❌ Video topilmadi.")
        return

    processing = await callback.message.answer("⏳ Audio ajratilmoqda...")
    video_path = get_temp_path("mp4")
    audio_path = get_temp_path("mp3")

    try:
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, destination=video_path)
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, extract_audio_from_video, video_path, audio_path)
        
        audio_file = FSInputFile(audio_path, filename="audio.mp3")
        await callback.message.answer_audio(audio=audio_file, caption="🎵 Videodan ajratilgan audio")
        await processing.delete()

    except Exception as e:
        await processing.edit_text(f"❌ Xatolik: {str(e)}")
    finally:
        cleanup_file(video_path)
        cleanup_file(audio_path)