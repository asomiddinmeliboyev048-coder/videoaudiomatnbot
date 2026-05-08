import os
import asyncio
from groq import Groq
from config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

async def process_audio(audio_path: str) -> str:
    """
    Ovozni matnga o'girish va chalkashliklarni bartaraf etish.
    """
    try:
        # 1. Whisper transkripsiyasi (Qat'iy o'zbek tilida)
        with open(audio_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=audio_file,
                language="uz", # Avtomatik aniqlashni o'chirib, 'uz' qo'yamiz
                response_format="verbose_json", # Til haqida ma'lumot olish uchun
                prompt="Bu o'zbek tilidagi audio: men, sen, u, biz, siz, ular, yaxshi, rahmat."
            )
        
        # Whisper ba'zida baribir boshqa tilni aniqlab yuborishi mumkin
        detected_lang = response.language.lower() if hasattr(response, 'language') else "uzbek"
        raw_text = response.text.strip()
        
        if not raw_text:
            return ""

        # 2. Llama tahriri - Agar Whisper adashgan bo'lsa, uni to'g'irlaydi
        # Skrinshotingizdagi "Urdu" yoki "Kazakh" xatoliklarini mana shu qism tozalaydi
        final_text = await force_uzbek_correction(raw_text)
        
        return final_text

    except Exception as e:
        print(f"Xatolik: {e}")
        return ""

async def force_uzbek_correction(text: str) -> str:
    """
    Har qanday tushunarsiz yoki boshqa tildagi matnni o'zbekcha lotinga majburlaydi.
    """
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Siz faqat o'zbek tili (lotin alifbosi) bo'yicha mutaxassissiz. "
                        "QOIDA: Sizga qanday tilda matn berilishidan qat'iy nazar, "
                        "uni mantiqan o'zbekcha lotin alifbosiga o'giring yoki tahrirlang. "
                        "Agar matn mutlaqo tushunarsiz bo'lsa (shovqin bo'lsa), uni o'zbekcha so'zlar bilan mazmunli qiling. "
                        "Faqat toza o'zbekcha matnni qaytaring, ortiqcha izohsiz."
                    )
                },
                {"role": "user", "content": text}
            ],
            temperature=0.1 # Ijodiylikni minimal qilish
        )
        return response.choices[0].message.content.strip()
    except:
        return text