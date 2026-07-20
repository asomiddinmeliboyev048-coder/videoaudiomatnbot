import logging
import os
from functools import lru_cache

import google.generativeai as genai

from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

# gemini-1.5-flash o'chirilgan. Modelni deployment environment orqali
# kodni o'zgartirmasdan almashtirish mumkin.
GEMINI_OCR_MODEL = os.getenv("GEMINI_OCR_MODEL", "gemini-2.5-flash")
GEMINI_TIMEOUT_SECONDS = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "120"))

_NO_TEXT_MARKERS = {
    "<no_text>",
    "rasmda matn topilmadi",
    "rasmdа matn topilmadi",
    "no text found",
}

_OCR_PROMPT = (
    "Rasmdagi barcha ko'rinadigan matnni aynan qanday yozilgan bo'lsa, "
    "o'sha tartibda ko'chirib yoz. Matn qaysi tilda va qaysi alifboda "
    "bo'lsa, aynan shu til va alifboda qoldir. Tarjima qilma, imlosini "
    "tuzatma, mazmunini o'zgartirma. Hech qanday izoh, sarlavha, Markdown "
    "yoki kod bloki qo'shma. Qatorlar va abzatslarni imkon qadar saqla. "
    "Agar rasmda matn bo'lmasa, faqat <NO_TEXT> yoz."
)


class OCRServiceError(RuntimeError):
    """Rasmni o'qish xizmati ishlamaganida ko'tariladi."""


@lru_cache(maxsize=1)
def _get_model():
    if not GEMINI_API_KEY:
        raise OCRServiceError("GEMINI_API_KEY sozlanmagan.")

    genai.configure(api_key=GEMINI_API_KEY)
    return genai.GenerativeModel(GEMINI_OCR_MODEL)


def _image_mime_type(image_bytes: bytes) -> str:
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    raise OCRServiceError("Faqat JPG, PNG va WEBP rasmlar qo'llab-quvvatlanadi.")


def _response_text(response) -> str:
    """Gemini javobidan matnni SDK response turidan xavfsiz ajratadi."""
    try:
        return (response.text or "").strip()
    except (AttributeError, ValueError):
        parts = []
        for candidate in getattr(response, "candidates", None) or []:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", None) or []:
                text = getattr(part, "text", None)
                if text:
                    parts.append(text)
        return "\n".join(parts).strip()


def _normalize_result(text: str) -> str:
    normalized = text.strip()

    # Model ko'rsatmaga qaramay butun javobni code fence ichiga olsa, faqat
    # tashqi Markdown qobig'ini olib tashlaymiz; OCR matnining o'zi o'zgarmaydi.
    lines = normalized.splitlines()
    if len(lines) >= 2 and lines[0].strip().startswith("```"):
        if lines[-1].strip() == "```":
            normalized = "\n".join(lines[1:-1]).strip()

    comparable = normalized.casefold().strip(" .!?'\"`")
    if not normalized or comparable in _NO_TEXT_MARKERS:
        return ""
    return normalized


def extract_text_from_image(image_path: str) -> str:
    """Rasmdagi matnni Gemini Vision orqali aynan asl tilida OCR qiladi."""
    if not os.path.isfile(image_path):
        raise OCRServiceError(f"Rasm fayli topilmadi: {image_path}")

    try:
        with open(image_path, "rb") as image_file:
            image_bytes = image_file.read()

        if not image_bytes:
            raise OCRServiceError("Rasm fayli bo'sh.")

        mime_type = _image_mime_type(image_bytes)
        image_part = {
            "mime_type": mime_type,
            "data": image_bytes,
        }

        response = _get_model().generate_content(
            [_OCR_PROMPT, image_part],
            generation_config={
                "temperature": 0.0,
                "candidate_count": 1,
                "max_output_tokens": 4096,
            },
            request_options={"timeout": GEMINI_TIMEOUT_SECONDS},
        )

        text = _normalize_result(_response_text(response))
        logger.info("Gemini OCR tugadi: model=%s", GEMINI_OCR_MODEL)
        return text
    except OCRServiceError:
        raise
    except Exception as exc:
        logger.exception(
            "Gemini OCR xatoligi: model=%s, xato_turi=%s",
            GEMINI_OCR_MODEL,
            type(exc).__name__,
        )
        raise OCRServiceError("Rasmni o'qish xizmati ishlamadi.") from exc
