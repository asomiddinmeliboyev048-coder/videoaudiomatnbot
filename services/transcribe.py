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
    Ovozni matnga o'girish. 
    Ovoz qaysi tilda bo'lsa, o'sha tilda matn qaytaradi (tarjima qilmaydi).
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
                    response_format="text" # To'g'ridan-to'g'ri matn qaytaradi
                )

        # AI so'rovini yuboramiz
        raw_text = await loop.run_in_executor(None, transcribe)

        if not raw_text:
            return ""

        return raw_text.strip()

    except Exception as e:
        logger.error(f"Transkripsiya xatoligi: {e}")
        return ""