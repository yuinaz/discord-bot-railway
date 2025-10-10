import os
import logging
import re
from typing import Any

import discord
from discord.ext import commands

log = logging.getLogger(__name__)

LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))

_RULES_RE = re.compile(r"rules|⛔", re.IGNORECASE)

def _is_rules_channel(dest: Any) -> bool:
    name = getattr(dest, "name", "") or ""
    return bool(_RULES_RE.search(name))

async def _safe_send(dest, *args, **kwargs):
    """Send dengan fallback: kalau Forbidden, alihkan ke log channel bila ada."""
    try:
        return await dest.send(*args, **kwargs)
    except discord.Forbidden:
        if LOG_CHANNEL_ID:
            bot = getattr(dest, "_state", None) and getattr(dest._state, "_get_client", None) and dest._state._get_client()
            # ^ cara aman dapat bot dari state, bisa None; fallback tidak wajib
            if bot and hasattr(bot, "get_channel"):
                ch = bot.get_channel(LOG_CHANNEL_ID) or await bot.fetch_channel(LOG_CHANNEL_ID)
                try:
                    warn = kwargs.copy()
                    warn["content"] = "[focus_final] rerouted (Forbidden)"
                    return await ch.send(*args, **warn)
                except Exception:
                    pass
        raise

class FocusLogRouterFinal(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _patch_send(self):
        # idempotent
        if getattr(self.bot, "_focus_final_patched", False):
            return
        self.bot._focus_final_patched = True

        orig_send = discord.abc.Messageable.send

        async def routed_send(self, *args, **kwargs):
            # block kirim ke #rules
            if _is_rules_channel(self):
                log.info("[focus_final] blocked send to #%s", getattr(self, "name", self))
                if LOG_CHANNEL_ID:
                    try:
                        ch = self._state._get_client().get_channel(LOG_CHANNEL_ID) or await self._state._get_client().fetch_channel(LOG_CHANNEL_ID)
                        return await ch.send("[focus_final] blocked a send to #rules", *args, **kwargs)
                    except Exception:
                        pass
                # drop saja
                return None
            # normal path dengan fallback Forbidden
            return await _safe_send(self, *args, **kwargs)

        # monkey patch
        discord.abc.Messageable.send = routed_send
        log.info("[focus_log_router_final] installed")

    @commands.Cog.listener()
    async def on_ready(self):
        await self._patch_send()

async def setup(bot: commands.Bot):
    cog = FocusLogRouterFinal(bot)
    await bot.add_cog(cog)
    await cog._patch_send()
