from __future__ import annotations
import logging
from typing import AsyncIterator
from discord.ext import commands
from discord.abc import Messageable

log = logging.getLogger(__name__)

_ORIG_HISTORY = None

async def _history_proxy(self: Messageable, *args, **kwargs) -> AsyncIterator["discord.Message"]:
    async for m in _ORIG_HISTORY(self, *args, **kwargs):
        try:
            cog = getattr(self, "bot", None) and self.bot.get_cog("RLShimHistory")
            if cog and hasattr(cog, "_record"):
                await cog._record(m)
        except Exception:
            pass
        yield m

class RLShimHistory(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        global _ORIG_HISTORY
        try:
            if _ORIG_HISTORY is None and hasattr(Messageable, "history"):
                _ORIG_HISTORY = Messageable.history
                if not getattr(Messageable, "_rlshim_patched", False):
                    Messageable.history = _history_proxy
                    setattr(Messageable, "_rlshim_patched", True)
                    log.info("[rl_shim_history] history() patched on Messageable")
        except Exception as e:
            log.warning("[rl_shim_history] patch skipped: %s", e)

    async def cog_unload(self):
        global _ORIG_HISTORY
        try:
            if _ORIG_HISTORY and getattr(Messageable, "_rlshim_patched", False):
                Messageable.history = _ORIG_HISTORY
                setattr(Messageable, "_rlshim_patched", False)
                _ORIG_HISTORY = None
                log.info("[rl_shim_history] history() unpatched")
        except Exception:
            pass

    async def _record(self, message: "discord.Message"):
        return

async def setup(bot: commands.Bot):
    await bot.add_cog(RLShimHistory(bot))
