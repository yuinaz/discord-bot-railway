import discord

async def handle_on_message(message: discord.Message, bot=None):
    # Abaikan pesan dari bot
    if getattr(message.author, "bot", False):
        return

    content = (message.content or '').strip()

    # Jika command prefix "!", serahkan ke parser command (jangan ditangani di handler custom)
    if content.startswith('!'):
        return

    # --- TARUH LOGIKA CUSTOM DI SINI (deteksi phishing/ocr/dll) ---
    # pass

    # PENTING: di akhir selalu teruskan ke parser command (sekali saja)
    try:
        await message.bot.process_commands(message)
    except Exception:
        pass
