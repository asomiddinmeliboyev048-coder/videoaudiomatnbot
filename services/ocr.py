import base64
import logging
import os
from functools import lru_cache
from typing import Optional

from groq import Groq

from config import GROQ_API_KEY, GROQ_TIMEOUT_SECONDS, OCR_MODELS

logger = logging.getLogger(__name__)

_NO_TEXT_MARKERS = {
    "<no_text>",
    "rasmda matn topilmadi",
    "rasmdа matn topilmadi",  # Eski promptdagi kirill `а` bilan yozilgan variant.
    "no text found",
}


class OCRServiceError(RuntimeError):
    """Rasmni o'qish xizmati ishlamaganida ko'tariladi."""


@lru_cache(maxsize=1)
def _get_client() -> Groq:
    if not GROQ_API_KEY:
        raise OCRServiceError("GROQ_API_KEY sozlanmagan.")
    return Groq(
        api_key=GROQ_API_KEY,
        timeout=GROQ_TIMEOUT_SECONDS,
        max_retries=0,
    )


def _detect_mime_type(image_bytes: bytes) -> str:
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image_bytes.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    raise OCRServiceError("Rasm formati qo'llab-quvvatlanmaydi.")


def _read_with_model(model: str, data_url: str) -> str:
    response = _get_client().chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Rasmdagi barcha ko'rinadigan matnni aynan yozilgan tilida "
                            "va yozuvida ko'chirib yoz. Tarjima qilma, mazmunini o'zgartirma, "
                            "izoh va Markdown qo'shma. Qatorlar va abzatslarni imkon qadar "
                            "saqla. Hech qanday matn bo'lmasa faqat <NO_TEXT> yoz."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        temperature=0.0,
        max_tokens=3000,
    )
    content = response.choices[0].message.content
    return (content or "").strip()


def _normalize_result(text: str) -> str:
    normalized = text.strip()
    comparable = normalized.casefold().strip(" .!?'\"`")
    if not normalized or comparable in _NO_TEXT_MARKERS:
        return ""
    return normalized


def extract_text_from_image(image_path: str) -> str:
    """Rasmdagi matnni tarjima qilmasdan, asl tilida OCR qiladi."""
    if not os.path.isfile(image_path):
        raise OCRServiceError(f"Rasm fayli topilmadi: {image_path}")

    with open(image_path, "rb") as image_file:
        image_bytes = image_file.read()

    if not image_bytes:
        raise OCRServiceError("Rasm fayli bo'sh.")

    mime_type = _detect_mime_type(image_bytes)
    encoded_image = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:{mime_type};base64,{encoded_image}"

    last_error: Optional[Exception] = None
    saw_no_text = False
    for model in OCR_MODELS:
        try:
            text = _normalize_result(_read_with_model(model, data_url))
            logger.info("OCR tugadi: model=%s", model)
            if text:
                return text
            saw_no_text = True
        except OCRServiceError:
            raise
        except Exception as exc:
            last_error = exc
            logger.warning(
                "OCR modeli ishlamadi: model=%s, status=%s, xato=%s",
                model,
                getattr(exc, "status_code", "noma'lum"),
                exc,
            )

    if saw_no_text:
        return ""

    if last_error is not None:
        logger.error(
            "Barcha OCR modellari ishlamadi",
            exc_info=(
                type(last_error),
                last_error,
                last_error.__traceback__,
            ),
        )
    raise OCRServiceError(
        "Rasmni o'qish xizmati vaqtincha ishlamadi."
    ) from last_error
