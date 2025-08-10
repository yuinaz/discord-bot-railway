# modules/discord_bot/message_handlers.py
import discord
from modules.discord_bot.handlers.url_guard import check_message_urls
from modules.discord_bot.handlers.invite_guard import check_nsfw_invites
from modules.discord_bot.handlers.image_handler import handle_image_check
from modules.discord_bot.handlers.ocr_handler import handle_ocr_check
from modules.discord_bot.handlers.image_classifier_guard import handle_image_classifier

async def handle_on_message(message: discord.Message, bot=None):
    # Abaikan pesan dari bot
    if message.author.bot:
        return

    # Pemeriksaan gambar & classifier lebih dulu (jika ada lampiran)
    try:
        await handle_image_check(message)
    except Exception:
        pass
    try:
        await handle_image_classifier(message)
    except Exception:
        pass

    # Pemeriksaan URL & undangan NSFW
    try:
        await check_message_urls(message, bot)
    except Exception:
        pass
    try:
        await check_nsfw_invites(message, bot)
    except Exception:
        pass

    # Pemeriksaan OCR (teks dalam gambar)
    try:
        await handle_ocr_check(message)
    except Exception:
        pass


# === IMPORTANT: forward to command parser ===
async def _ensure_process_commands(message):
    try:
        await message.bot.process_commands(message)
    except Exception:
        pass
