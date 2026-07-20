import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID")  # masalan: @mening_kanalim
CHANNEL_LINK = os.getenv("CHANNEL_LINK")  # masalan: https://t.me/mening_kanalim

MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
TEMP_DIR = os.getenv("TEMP_DIR", "temp_files")
GROQ_TIMEOUT_SECONDS = float(os.getenv("GROQ_TIMEOUT_SECONDS", "120"))
MAX_TRANSCRIPTION_FILE_SIZE_MB = int(
    os.getenv("MAX_TRANSCRIPTION_FILE_SIZE_MB", "24")
)
TRANSCRIPTION_MODEL = os.getenv("TRANSCRIPTION_MODEL", "whisper-large-v3")

# Birinchi model ishlamasa, vergul bilan ajratilgan keyingi modellar sinab ko'riladi.
# Model nomlarini deployment environment orqali kodni o'zgartirmasdan yangilash mumkin.
OCR_MODELS = tuple(
    model.strip()
    for model in os.getenv(
        "OCR_MODELS",
        (
            "meta-llama/llama-4-maverick-17b-128e-instruct,"
            "meta-llama/llama-4-scout-17b-16e-instruct"
        ),
    ).split(",")
    if model.strip()
)

if not OCR_MODELS:
    raise ValueError("OCR_MODELS kamida bitta model nomini o'z ichiga olishi kerak.")
