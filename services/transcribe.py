import os
import asyncio
import logging
from groq import Groq
from config import GROQ_API_KEY

# Loglarni sozlash
logger = logging.getLogger(__name__)

# Groq mijozini yaratish
client = Groq(api_key=GROQ_API_KEY)

async def process_audio(audio_path: str) -> str:
    """
    Ovozni matnga o'girish. O'zbek tili grammatikasiga urg'u berilgan.
    Ovozli xabar va videolar uchun universal transkripsiya.
    """
    try:
        # Fayl mavjudligini tekshirish
        if not os.path.exists(audio_path):
            logger.error(f"Fayl topilmadi: {audio_path}")
            return ""

        # Groq sinxron kutubxona bo'lgani uchun uni executor ichida ishlatamiz
        loop = asyncio.get_event_loop()
        
        def transcribe():
            with open(audio_path, "rb") as audio_file:
                # Transcriptions metodi ovozni o'z tilida yozib beradi
                return client.audio.transcriptions.create(
                    model="whisper-large-v3",
                    file=(os.path.basename(audio_path), audio_file.read()),
                    # Prompt - Whisper'ni o'zbek tiliga moslashga majbur qiladi
                    prompt="Bu o'zbek tilidagi audio. Men, sen, u, biz, siz, ular. O'zbek tili qoidalariga amal qilinsin.",
                    response_format="text"
                )

        # AI so'rovini yuboramiz
        raw_text = await loop.run_in_executor(None, transcribe)

        if not raw_text:
            return ""

        return raw_text.strip()

    except Exception as e:
        logger.error(f"Transkripsiya xatoligi: {e}")
        return ""