
import os
import time
import asyncio
import logging
from discord.ext import commands

# Throttle every page fetch of channel.history() to avoid GET /messages 429s
_log = logging.getLogger(__name__)
_original_next = None
_lock = asyncio.Lock()
_last_call = 0.0

def _get_min_interval():
    try:
        return float(os.getenv("RL_SHIM_HISTORY_MIN_INTERVAL", "0.85"))
    except Exception:
        return 0.85

async def _throttle():
    global _last_call
    async with _lock:
        now = time.monotonic()
        delay = _get_min_interval() - (now - _last_call)
        if delay > 0:
            await asyncio.sleep(delay)
        _last_call = time.monotonic()

class RLShimHistory(commands.Cog):
    """Monkeypatch discord.iterators.HistoryIterator.next to add a small delay.
    This reduces Discord 429s caused by concurrent history() calls during startup.
    Controlled by env RL_SHIM_HISTORY_MIN_INTERVAL (seconds). Default 0.85s.
    """
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        global _original_next
        if _original_next is not None:
            return
        try:
            import discord.iterators as iters
            _original_next = iters.HistoryIterator.next

            async def patched_next(self_, *args, **kwargs):
                await _throttle()
                return await _original_next(self_, *args, **kwargs)

            iters.HistoryIterator.next = patched_next  # type: ignore[attr-defined]
            _log.info("[rl_shim_history] patched HistoryIterator.next (min_interval=%ss)", _get_min_interval())
        except Exception:
            _log.exception("[rl_shim_history] patch failed")

    async def cog_unload(self):
        global _original_next
        if _original_next is not None:
            try:
                import discord.iterators as iters
                iters.HistoryIterator.next = _original_next  # type: ignore[attr-defined]
                _original_next = None
                _log.info("[rl_shim_history] unpatched HistoryIterator.next")
            except Exception:
                _log.exception("[rl_shim_history] unpatch failed")

async def setup(bot):
    await bot.add_cog(RLShimHistory(bot))
