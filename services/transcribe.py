import asyncio
import logging
import os
from functools import lru_cache

from groq import Groq

from config import (
    GROQ_API_KEY,
    GROQ_TIMEOUT_SECONDS,
    MAX_TRANSCRIPTION_FILE_SIZE_MB,
    TRANSCRIPTION_MODEL,
)

logger = logging.getLogger(__name__)


class TranscriptionError(RuntimeError):
    """Audio transkripsiya xizmati ishlamaganida ko'tariladi."""


@lru_cache(maxsize=1)
def _get_client() -> Groq:
    if not GROQ_API_KEY:
        raise TranscriptionError("GROQ_API_KEY sozlanmagan.")
    return Groq(api_key=GROQ_API_KEY, timeout=GROQ_TIMEOUT_SECONDS)


def _transcribe_sync(audio_path: str) -> str:
    """Groq SDK'ning sinxron chaqiruvini alohida threadda bajaradi."""
    with open(audio_path, "rb") as audio_file:
        response = _get_client().audio.transcriptions.create(
            model=TRANSCRIPTION_MODEL,
            file=(os.path.basename(audio_path), audio_file.read()),
            response_format="text",
            temperature=0.0,
        )

    if isinstance(response, str):
        return response.strip()

    # SDK versiyasiga qarab text response obyekt bo'lib qaytishi ham mumkin.
    return (getattr(response, "text", "") or "").strip()


async def process_audio(audio_path: str) -> str:
    """
    Audioni tarjima qilmasdan, avtomatik aniqlangan asl tilida transkripsiya qiladi.

    Muhim: `translations` endpointi, `language` va tilga majburlovchi `prompt`
    ishlatilmaydi. Shu sabab Whisper o'zbek, ingliz, rus va boshqa tillarni
    audioning o'zidan avtomatik aniqlaydi.
    """
    if not os.path.isfile(audio_path):
        raise TranscriptionError(f"Audio fayl topilmadi: {audio_path}")
    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    if file_size_mb == 0:
        raise TranscriptionError("Audio fayl bo'sh.")
    if file_size_mb > MAX_TRANSCRIPTION_FILE_SIZE_MB:
        raise TranscriptionError(
            "Audio fayl Groq limitidan katta: "
            f"{file_size_mb:.1f} MB (maksimum "
            f"{MAX_TRANSCRIPTION_FILE_SIZE_MB} MB)."
        )

    try:
        loop = asyncio.get_running_loop()
        text = await loop.run_in_executor(None, _transcribe_sync, audio_path)
        logger.info("Transkripsiya tugadi: model=%s", TRANSCRIPTION_MODEL)
        return text
    except TranscriptionError:
        raise
    except Exception as exc:
        logger.exception("Transkripsiya xizmati xatoligi")
        raise TranscriptionError(
            "Audio matnga aylantirish xizmati vaqtincha ishlamadi."
        ) from exc
