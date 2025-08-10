import discord

async def handle_on_message(message: discord.Message, bot=None):
    # Abaikan pesan dari bot
    if getattr(message.author, "bot", False):
        return

    content = (message.content or '').strip()

    # Panggil parser command maksimal sekali per message dengan guard
    def _should_process(msg):
        return not getattr(msg, "_sb_pc_done", False)

    # Jika command prefix "!", jangan proses logic custom
    if content.startswith('!'):
        if _should_process(message):
            message._sb_pc_done = True
            try:
                await message.bot.process_commands(message)
            except Exception:
                pass
        return

    # --- TARUH LOGIKA CUSTOM DI SINI (deteksi phishing/ocr/dll) ---
    # pass

    if _should_process(message):
        message._sb_pc_done = True
        try:
            await message.bot.process_commands(message)
        except Exception:
            pass
