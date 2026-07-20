import os
import tempfile

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID")  # masalan: @mening_kanalim
CHANNEL_LINK = os.getenv("CHANNEL_LINK")  # masalan: https://t.me/mening_kanalim

MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
# /tmp kabi system temp katalogi deploylarda odatda yozish uchun ochiq bo'ladi.
TEMP_DIR = os.getenv(
    "TEMP_DIR",
    os.path.join(tempfile.gettempdir(), "videoaudiomatnbot"),
)
TRANSCRIPTION_MODEL = os.getenv("TRANSCRIPTION_MODEL", "whisper-large-v3")
MAX_TRANSCRIPTION_FILE_SIZE_MB = int(
    os.getenv("MAX_TRANSCRIPTION_FILE_SIZE_MB", "24")
)
GROQ_TIMEOUT_SECONDS = float(os.getenv("GROQ_TIMEOUT_SECONDS", "120"))
# MANA SHU QATOR YANGILANDI: preview o'rniga instruct yozildi
OCR_MODEL = os.getenv("OCR_MODEL", "llama-3.2-90b-vision")
FFMPEG_BINARY = os.getenv("FFMPEG_BINARY", "ffmpeg")

# Har user uchun saqlanadigan oxirgi savol-javob juftlari soni.
CHAT_HISTORY_TURNS = int(os.getenv("CHAT_HISTORY_TURNS", "8"))
# In-memory tarix saqlanadigan eng ko'p faol foydalanuvchilar soni.
CHAT_HISTORY_MAX_USERS = int(os.getenv("CHAT_HISTORY_MAX_USERS", "1000"))
