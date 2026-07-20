import asyncio
import logging
import os
from functools import lru_cache
from typing import Optional, Tuple

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
    return Groq(
        api_key=GROQ_API_KEY,
        timeout=GROQ_TIMEOUT_SECONDS,
        max_retries=2,
    )


def _extract_transcript(audio_path: str) -> Tuple[str, Optional[str]]:
    with open(audio_path, "rb") as audio_file:
        response = _get_client().audio.transcriptions.create(
            model=TRANSCRIPTION_MODEL,
            file=(os.path.basename(audio_path), audio_file),
            response_format="verbose_json",
            temperature=0.0,
        )

    if isinstance(response, str):
        return response.strip(), None

    text = getattr(response, "text", "") or ""
    language = getattr(response, "language", None)
    return text.strip(), language


async def process_audio(audio_path: str) -> str:
    """
    Audioni tarjima qilmasdan, manba tilining o'zida matnga aylantiradi.

    Til Groq Whisper tomonidan avtomatik aniqlanadi. `language` va tilga xos
    `prompt` ataylab yuborilmaydi: ular boshqa tillardagi audioni noto'g'ri
    tilga majburlashi mumkin.
    """
    if not os.path.isfile(audio_path):
        raise TranscriptionError(f"Audio fayl topilmadi: {audio_path}")
    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    if file_size_mb == 0:
        raise TranscriptionError("Audio fayl bo'sh.")
    if file_size_mb > MAX_TRANSCRIPTION_FILE_SIZE_MB:
        raise TranscriptionError(
            "Transkripsiya audiosi juda katta "
            f"({file_size_mb:.1f} MB; maksimum "
            f"{MAX_TRANSCRIPTION_FILE_SIZE_MB} MB)."
        )

    try:
        text, detected_language = await asyncio.to_thread(
            _extract_transcript, audio_path
        )
        logger.info(
            "Transkripsiya tugadi: model=%s, aniqlangan_til=%s",
            TRANSCRIPTION_MODEL,
            detected_language or "noma'lum",
        )
        return text
    except TranscriptionError:
        raise
    except Exception as exc:
        logger.exception("Transkripsiya xizmati xatoligi")
        raise TranscriptionError(
            "Audio matnga aylantirish xizmati vaqtincha ishlamadi."
        ) from exc
