# modules/discord_bot/helpers/tasks.py

import os
import discord
from discord.ext import commands
from datetime import datetime
from modules.discord_bot.helpers.image_hashing import calculate_image_hash
from modules.discord_bot.helpers.image_check import is_blacklisted_image, add_to_blacklist
from modules.discord_bot.helpers.image_utils import compress_image, convert_to_rgb
from modules.discord_bot.helpers.ocr_check import extract_text_from_image, contains_prohibited_text
from modules.logger.helpers.logger_utils import log_violation, log_image_event

async def process_image_message(message: discord.Message, bot: commands.Bot):
    """Proses pesan berisi gambar, cek hash & OCR jika perlu."""
    if not message.attachments:
        return

    for attachment in message.attachments:
        if not attachment.content_type or not attachment.content_type.startswith("image"):
            continue

        try:
            image_bytes = await attachment.read()
            image_hash = calculate_image_hash(image_bytes)

            if not image_hash:
                continue  # Tidak bisa hash gambar

            # Logging deteksi gambar (opsional)
            await await log_image_event(message, image_hash)

            if is_blacklisted_image(image_bytes):
                await handle_blacklisted_image(message, image_hash)
                return

            # Jalankan OCR check
            if await check_ocr_violation(image_bytes, message, image_hash):
                return

        except Exception as e:
            print(f"[❌] Gagal memproses attachment: {e}")

async def handle_blacklisted_image(message: discord.Message, image_hash: str):
    """Tindakan jika gambar termasuk dalam blacklist."""
    try:
        await message.delete()
        await message.channel.send(f"⚠️ Gambar diblokir (blacklist hash).", delete_after=10)
        await log_violation(message, image_hash, reason="Image hash in blacklist")
    except Exception as e:
        print(f"[❌] Gagal menghapus pesan blacklist: {e}")

async def check_ocr_violation(image_bytes: bytes, message: discord.Message, image_hash: str) -> bool:
    """Cek apakah teks dalam gambar melanggar melalui OCR."""
    try:
        text = extract_text_from_image(image_bytes)
        if text and contains_prohibited_text(text):
            await message.delete()
            await message.channel.send("🛑 Gambar mengandung teks terlarang.", delete_after=10)
            await await log_violation(message, image_hash, reason="Prohibited OCR text")
            return True
    except Exception as e:
        print(f"[❌] Gagal OCR: {e}")
    return False
