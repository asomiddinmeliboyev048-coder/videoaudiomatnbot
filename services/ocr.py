import base64
from groq import Groq
from config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)


def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def extract_text_from_image(image_path: str) -> str:
    """
    Rasmdagi matnni Groq (llama vision) yordamida o'qiydi.
    """
    base64_image = encode_image(image_path)

    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    },
                    {
                        "type": "text",
                        "text": (
                            "Ushbu rasmdagi barcha matnni to'liq va aniq o'qi. "
                            "Faqat rasmdagi matnni yoz, hech qanday izoh qo'shma. "
                            "Agar matn o'zbek tilida bo'lsa o'zbekcha yoz. "
                            "Agar boshqa tilda bo'lsa o'sha tildagi yozuvni yoz. "
                            "Agar rasmdа matn yo'q bo'lsa: 'Rasmdа matn topilmadi' deb yoz."
                        )
                    }
                ]
            }
        ],
        max_tokens=2000
    )

    return response.choices[0].message.content.strip()