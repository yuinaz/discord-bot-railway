
"""
Backward-compatible message handler.
- Menerima dua gaya pemanggilan:
    1) handle_on_message(bot, message)
    2) handle_on_message(message)  # lama
- Guard aman: proses setiap message sekali saja (tanpa mutasi Message).
- Selalu memanggil bot.process_commands(message).
"""
import asyncio
from collections import deque

_MSG_GUARD_LOCK = asyncio.Lock()
_MSG_SEEN_IDS = set()
_MSG_QUEUE = deque(maxlen=4096)

async def _guard_once(message_id: int) -> bool:
    if message_id is None:
        return True
    async with _MSG_GUARD_LOCK:
        if message_id in _MSG_SEEN_IDS:
            return False
        _MSG_SEEN_IDS.add(message_id)
        _MSG_QUEUE.append(message_id)
        if len(_MSG_QUEUE) == _MSG_QUEUE.maxlen:
            old = _MSG_QUEUE.popleft()
            _MSG_SEEN_IDS.discard(old)
        return True

async def handle_on_message(*args):
    """Dapat dipanggil sebagai handle_on_message(bot, message) atau handle_on_message(message)."""
    bot = None
    message = None

    if len(args) == 1:
        # Gaya lama: (message)
        message = args[0]
        # Ambil bot dari state internal discord.py (aman di runtime)
        bot = getattr(getattr(message, "_state", None), "_get_client", lambda: None)()
    elif len(args) >= 2:
        bot, message = args[0], args[1]

    if message is None or bot is None:
        return  # tidak bisa proses

    # Skip DM / bot
    if getattr(message, "author", None) and getattr(message.author, "bot", False):
        return
    if getattr(message, "guild", None) is None:
        return

    # Pastikan hanya sekali per message
    mid = getattr(message, "id", None)
    if not await _guard_once(mid):
        return

    # >>> tempatkan pre-processor lain bila perlu <<<

    # Penting: teruskan ke command processor
    await bot.process_commands(message)
