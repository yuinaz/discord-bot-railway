
"""
Safe message handler:
- Tidak lagi menempelkan atribut ke discord.Message (menghindari AttributeError).
- Memastikan bot.process_commands(message) dieksekusi sekali per message.
- Ringan, thread-safe dengan asyncio.Lock + LRU set.
"""
import asyncio
from collections import deque

# LRU guard agar setiap message hanya diproses sekali
_MSG_GUARD_LOCK = asyncio.Lock()
_MSG_SEEN_IDS = set()
_MSG_QUEUE = deque(maxlen=4096)

async def _guard_once(message_id: int) -> bool:
    """Return True jika message_id belum pernah diproses (lalu tandai), False jika duplikat."""
    if message_id is None:
        return True  # kalau tak ada ID, biarkan lewat (jarang terjadi)
    async with _MSG_GUARD_LOCK:
        if message_id in _MSG_SEEN_IDS:
            return False
        _MSG_SEEN_IDS.add(message_id)
        _MSG_QUEUE.append(message_id)
        # Buang ID lama bila melebihi kapasitas (deque sudah otomatis FIFO)
        if len(_MSG_QUEUE) == _MSG_QUEUE.maxlen:
            old = _MSG_QUEUE.popleft()
            _MSG_SEEN_IDS.discard(old)
        return True

async def handle_on_message(bot, message):
    """Panggil ini dari event on_message utama kamu.
    Contoh:
        @bot.event
        async def on_message(message):
            from modules.discord_bot import message_handlers
            await message_handlers.handle_on_message(bot, message)
    """
    # Abaikan DM / bot
    if getattr(message, "author", None) and getattr(message.author, "bot", False):
        return
    if getattr(message, "guild", None) is None:
        return

    # Pastikan hanya sekali per message
    mid = getattr(message, "id", None)
    if not await _guard_once(mid):
        return

    # >>> Taruh handler/praproses lain di sini jika perlu <<<
    # Contoh: anti-spam, anti-phish, dsb. (cog on_message akan tetap dipanggil oleh Discord)

    # Penting: selalu panggil process_commands agar prefix commands (!testban, dst.) tetap jalan
    await bot.process_commands(message)
