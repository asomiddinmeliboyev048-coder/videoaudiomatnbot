import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID")        # masalan: @mening_kanalim
CHANNEL_LINK = os.getenv("CHANNEL_LINK")    # masalan: https://t.me/mening_kanalim

MAX_FILE_SIZE_MB = 50
TEMP_DIR = "temp_files"