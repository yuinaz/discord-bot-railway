import discord
from typing import Set
_SB_PROCESSED_IDS: Set[int] = set()

def _should_process(msg: discord.Message) -> bool:
    try:
        mid = msg.id
    except Exception:
        return True
    return mid not in _SB_PROCESSED_IDS

def _mark_processed(msg: discord.Message) -> None:
    try:
        _SB_PROCESSED_IDS.add(msg.id)
    except Exception:
        pass

async def handle_on_message(message: discord.Message, bot=None):
    # Abaikan pesan dari bot
    if getattr(message.author, "bot", False):
        return

    content = (message.content or '').strip()

    # Panggil parser command maksimal sekali per message dengan guard
    # Jika command prefix "!", jangan proses logic custom
    if content.startswith('!'):
        if _should_process(message):
            _mark_processed(message)
            try:
                await message.bot.process_commands(message)
            except Exception:
                pass
        return

    # --- TARUH LOGIKA CUSTOM DI SINI (deteksi phishing/ocr/dll) ---
    # pass

    if _should_process(message):
        _mark_processed(message)
        try:
            await message.bot.process_commands(message)
        except Exception:
            pass
