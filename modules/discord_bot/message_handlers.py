import discord

async def handle_on_message(message: discord.Message, bot=None):
    # Abaikan pesan dari bot
    if getattr(message.author, "bot", False):
        return

    content = (message.content or '').strip()

    # Jika ini command prefix "!", jangan diproses di handler custom
    if content.startswith('!'):
        return

    # --- TARUH LOGIKA CUSTOM DI SINI (deteksi phishing/ocr/dll) ---
    # (Dibiarkan kosong supaya tidak mengganggu command. Tambahkan kembali logic kamu bila perlu.)
    return

# Pastikan semua pesan akhirnya tetap diteruskan ke parser command
async def _ensure_process_commands(message: discord.Message):
    try:
        await message.bot.process_commands(message)
    except Exception:
        pass
