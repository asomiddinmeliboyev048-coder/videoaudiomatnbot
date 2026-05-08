from aiogram import Router, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart

from handlers.subscription import check_subscription
from config import CHANNEL_LINK

router = Router()


def get_subscribe_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanalga a'zo bo'lish", url=CHANNEL_LINK)],
        [InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")]
    ])


def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ℹ️ Bot haqida", callback_data="about_bot")]
    ])


BOT_INFO = """
🤖 <b>Video Audio Matn Bot</b>

<b>Bot nima qila oladi:</b>

🎬 <b>Video yuborsangiz:</b>
  📝 <b>Matnni olish</b> — Videodagi gaplarni matnga aylantiradi
  🎵 <b>Audioni olish</b> — Videodan MP3 audio ajratib beradi

🖼️ <b>Rasm yuborsangiz:</b>
  📄 Rasmdagi yozuvlarni o'qib, matn ko'rinishida yuboradi

🌍 <b>Tillar:</b>
  • O'zbek tilida video → o'zbekcha matn
  • Chet el tilida video → o'sha tildagi matn
  • Rasmdagi har qanday til → aniq matn

⚡ Maksimal fayl hajmi: 50 MB
"""


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    user_id = message.from_user.id
    name = message.from_user.first_name

    is_sub = await check_subscription(bot, user_id)

    if is_sub:
        await message.answer(
            f"👋 Xush kelibsiz, <b>{name}</b>!\n\n"
            f"✅ <b>Obunangiz tasdiqlandi!</b>\n\n"
            f"{BOT_INFO}",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
    else:
        await message.answer(
            f"👋 Salom, <b>{name}</b>!\n\n"
            f"🔒 Botdan foydalanish uchun avval kanalimizga a'zo bo'ling:\n\n"
            f"⬇️ Quyidagi tugmani bosing:",
            parse_mode="HTML",
            reply_markup=get_subscribe_keyboard()
        )


@router.callback_query(lambda c: c.data == "check_sub")
async def check_sub_callback(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    is_sub = await check_subscription(bot, user_id)

    if is_sub:
        await callback.message.edit_text(
            f"✅ <b>Obunangiz tasdiqlandi!</b>\n\n{BOT_INFO}",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
    else:
        await callback.answer(
            "❌ Hali kanalga a'zo bo'lmadingiz! Avval a'zo bo'ling.",
            show_alert=True
        )


@router.callback_query(lambda c: c.data == "about_bot")
async def about_callback(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(BOT_INFO, parse_mode="HTML")