import base64
import logging
import os
from functools import lru_cache

from groq import Groq

from config import GROQ_API_KEY, GROQ_TIMEOUT_SECONDS, OCR_MODEL

logger = logging.getLogger(__name__)

_NO_TEXT_MARKERS = {
    "<no_text>",
    "rasmda matn topilmadi",
    "rasmdа matn topilmadi",
    "no text found",
}


class OCRServiceError(RuntimeError):
    """Rasmni o'qish xizmati ishlamaganida ko'tariladi."""


@lru_cache(maxsize=1)
def _get_client() -> Groq:
    if not GROQ_API_KEY:
        raise OCRServiceError("GROQ_API_KEY sozlanmagan.")
    # SDK'ning standart timeout va retry sozlamalari ishlatiladi. Avval ishlagan
    # request bilan moslikni saqlash uchun max_retries majburan o'zgartirilmaydi.
    return Groq(api_key=GROQ_API_KEY, timeout=GROQ_TIMEOUT_SECONDS)


def _image_mime_type(image_bytes: bytes) -> str:
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    raise OCRServiceError("Faqat JPG, PNG va WEBP rasmlar qo'llab-quvvatlanadi.")


def _normalize_result(text: str) -> str:
    normalized = text.strip()
    comparable = normalized.casefold().strip(" .!?'\"`")
    if not normalized or comparable in _NO_TEXT_MARKERS:
        return ""
    return normalized


def extract_text_from_image(image_path: str) -> str:
    """Rasmdagi matnni tarjima qilmasdan, aynan asl tilida o'qiydi."""
    if not os.path.isfile(image_path):
        raise OCRServiceError(f"Rasm fayli topilmadi: {image_path}")

    try:
        with open(image_path, "rb") as image_file:
            image_bytes = image_file.read()

        if not image_bytes:
            raise OCRServiceError("Rasm fayli bo'sh.")

        mime_type = _image_mime_type(image_bytes)
        base64_image = base64.b64encode(image_bytes).decode("utf-8")

        # Image-first tartibi va Scout modeli botning avval ishlagan Groq Vision
        # request shakliga qaytarildi. Telegram photo bu yerga bytes sifatida keladi.
        response = _get_client().chat.completions.create(
            model=OCR_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": (
                                    f"data:{mime_type};base64,{base64_image}"
                                )
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "Rasmdagi barcha ko'rinadigan matnni to'liq va "
                                "aniq ko'chirib yoz. Matnni tarjima qilma va tilini "
                                "o'zgartirma. Faqat rasmdagi matnni yoz, izoh yoki "
                                "Markdown qo'shma. Hech qanday matn bo'lmasa faqat "
                                "<NO_TEXT> yoz."
                            ),
                        },
                    ],
                }
            ],
            temperature=0.0,
            max_tokens=3000,
        )

        content = response.choices[0].message.content or ""
        logger.info("OCR tugadi: model=%s", OCR_MODEL)
        return _normalize_result(content)
    except OCRServiceError:
        raise
    except Exception as exc:
        logger.exception(
            "Groq OCR xatoligi: model=%s, status=%s",
            OCR_MODEL,
            getattr(exc, "status_code", "noma'lum"),
        )
        raise OCRServiceError("Rasmni o'qish xizmati ishlamadi.") from exc
