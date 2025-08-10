import discord
from modules.discord_bot.helpers.image_check import is_blacklisted_image
from modules.discord_bot.helpers.image_hashing import calculate_image_hash
from modules.discord_bot.logger_utils import log_blacklisted_image

async def handle_image_check(message: discord.Message):
    """Handle pengecekan gambar dalam pesan, hapus jika termasuk blacklist."""
    if not message.attachments:
        return

    for attachment in message.attachments:
        # Cek apakah file adalah gambar
        if not attachment.content_type or not attachment.content_type.startswith("image/"):
            continue

        try:
            image_bytes = await attachment.read()
            image_hash = calculate_image_hash(image_bytes)
            if not image_hash:
                continue

            if is_blacklisted_image(image_hash):
                await message.delete()
                await message.channel.send(
                    f"⚠️ Gambar milik {message.author.mention} termasuk **blacklist** dan telah dihapus.",
                    delete_after=10,
                )
                log_blacklisted_image(message, image_hash)

        except Exception as e:
            print(f"[Image Check Error] {e}")
