import asyncio
import logging
from aiogram import Router, Bot, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    FSInputFile
)

from handlers.subscription import check_subscription
from handlers.start import get_subscribe_keyboard
from services.transcribe import process_audio
from services.extract_audio import extract_audio_from_video
from services.ocr import extract_text_from_image
from utils.helpers import get_temp_path, cleanup_file

logger = logging.getLogger(__name__)
router = Router()

file_store: dict = {}
counter = 0

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

@router.message(F.video_note)
async def handle_video_note(message: Message, bot: Bot):
    if not await check_subscription(bot, message.from_user.id):
        await message.answer("🔒 Avval kanalga a'zo bo'ling:", reply_markup=get_subscribe_keyboard())
        return

    key = save_file_id(message.video_note.file_id)
    await message.answer("🎬 Video xabar qabul qilindi! Nima qilishni tanlang:", reply_markup=get_video_keyboard(key))

# ─── OVOZLI XABAR ─────────────────────────────────────────────────────────────

@router.message(F.voice)
async def handle_voice(message: Message, bot: Bot):
    if not await check_subscription(bot, message.from_user.id):
        await message.answer("🔒 Avval kanalga a'zo bo'ling:", reply_markup=get_subscribe_keyboard())
        return

    processing = await message.answer("🎤 Ovozli xabar tahlil qilinmoqda...")
    audio_path = get_temp_path("ogg")

    try:
        file = await bot.get_file(message.voice.file_id)
        await bot.download_file(file.file_path, destination=audio_path)

        # Yangilangan asinxron process_audio funksiyasini chaqiramiz
        text = await process_audio(audio_path)

        await processing.delete()

        if not text or not text.strip():
            await message.answer("⚠️ Ovozli xabarda matn topilmadi.")
        else:
            # Sarlavha yuborish va keyin matnni o'zini yuborish
            await message.answer("🎤 <b>Ovozli xabar matni:</b>", parse_mode="HTML")
            await send_long_text(message, text)
            await message.answer("✅ @ovozli1_bot orqali matnni ovozli qilib oling!")

    except Exception as e:
        await processing.edit_text(f"❌ Xatolik: {str(e)}")
    finally:
        cleanup_file(audio_path)

# ─── RASM ─────────────────────────────────────────────────────────────────────

@router.message(F.photo)
async def handle_photo(message: Message, bot: Bot):
    if not await check_subscription(bot, message.from_user.id):
        await message.answer("🔒 Avval kanalga a'zo bo'ling:", reply_markup=get_subscribe_keyboard())
        return

    processing = await message.answer("🔍 Rasmdagi matn o'qilmoqda, kuting...")
    image_path = get_temp_path("jpg")

    try:
        file = await bot.get_file(message.photo[-1].file_id)
        await bot.download_file(file.file_path, destination=image_path)

        # OCR funksiyasi hali sinxron bo'lishi mumkin, shuning uchun run_in_executor qoladi
        text = await asyncio.get_event_loop().run_in_executor(None, extract_text_from_image, image_path)

        await processing.delete()
        if not text:
            await message.answer("⚠️ Rasmdagi matn aniqlanmadi.")
        else:
            await message.answer("✅ <b>Rasmdagi matn:</b>", parse_mode="HTML")
            await send_long_text(message, text)
            await message.answer("✅ @ovozli1_bot orqali matnni ovozli qilib oling!")

    except Exception as e:
        await processing.edit_text(f"❌ Xatolik: {str(e)}")
    finally:
        cleanup_file(image_path)

# ─── CALLBACK: MATNNI OLISH (VIDEO UCHUN) ──────────────────────────────────────

@router.callback_query(lambda c: c.data and c.data.startswith("vt:"))
async def get_text_callback(callback: CallbackQuery, bot: Bot):
    key = callback.data[3:]
    file_id = get_file_id(key)
    await callback.answer()

    if not file_id:
        await callback.message.answer("❌ Video topilmadi. Iltimos, videoni qayta yuboring.")
        return

    processing = await callback.message.answer("⏳ Audio matnga aylantirilmoqda, kuting...")
    video_path = get_temp_path("mp4")
    audio_path = get_temp_path("mp3")

    try:
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, destination=video_path)

        # Audioni ajratib olish (sinxron xizmat bo'lsa run_in_executor qoladi)
        await asyncio.get_event_loop().run_in_executor(None, extract_audio_from_video, video_path, audio_path)

        # Transkripsiya (asinxron funksiya)
        text = await process_audio(audio_path)

        await processing.delete()

        if not text:
            await callback.message.answer("⚠️ Videoda aniqlanadigan ovoz topilmadi.")
        else:
            await callback.message.answer("✅ <b>Video matni:</b>", parse_mode="HTML")
            await send_long_text(callback.message, text)
            await callback.message.answer("✅ @ovozli1_bot orqali matnni ovozli qilib oling!")

    except Exception as e:
        await processing.edit_text(f"❌ Xatolik: {str(e)}")
    finally:
        cleanup_file(video_path)
        cleanup_file(audio_path)

# ─── CALLBACK: AUDIONI OLISH ──────────────────────────────────────────────────

@router.callback_query(lambda c: c.data and c.data.startswith("va:"))
async def get_audio_callback(callback: CallbackQuery, bot: Bot):
    key = callback.data[3:]
    file_id = get_file_id(key)
    await callback.answer()

    if not file_id:
        await callback.message.answer("❌ Video topilmadi. Iltimos, videoni qayta yuboring.")
        return

    processing = await callback.message.answer("⏳ Audio ajratilmoqda...")
    video_path = get_temp_path("mp4")
    audio_path = get_temp_path("mp3")

    try:
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, destination=video_path)

        await asyncio.get_event_loop().run_in_executor(None, extract_audio_from_video, video_path, audio_path)

        await processing.edit_text("✅ Audio tayyor! Yuborilmoqda...")
        audio_file = FSInputFile(audio_path, filename="audio.mp3")
        await callback.message.answer_audio(audio=audio_file, caption="🎵 Videodan ajratilgan audio\n✅ @MatnOvozBot")
        await processing.delete()

    except Exception as e:
        await processing.edit_text(f"❌ Xatolik: {str(e)}")
    finally:
        cleanup_file(video_path)
        cleanup_file(audio_path)