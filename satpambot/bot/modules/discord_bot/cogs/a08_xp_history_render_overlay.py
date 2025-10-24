from __future__ import annotations
import os, time, logging
try:
    import discord
    from discord.ext import commands
except Exception:
    class discord:  # type: ignore
        class Message: ...
    class commands:  # type: ignore
        class Cog:
            @staticmethod
            def listener(*a, **k):
                def _w(f): return f
                return _w
        @staticmethod
        def listener(*a, **k):
            def _w(f): return f
            return _w

try:
    from satpambot.bot.modules.discord_bot.helpers.upstash_client import UpstashClient
except Exception:
    UpstashClient = None

from satpambot.config.auto_defaults import cfg_int, cfg_str
log = logging.getLogger(__name__)

SENIOR_KEY = cfg_str("XP_SENIOR_KEY", "xp:bot:senior_total_v2")
DELTA_DEFAULT = int(cfg_str("XP_RENDER_DELTA_DEFAULT", "0") or "0")
SILENT_NO_SHIM = (cfg_str("XP_SILENT_NO_SHIM", "1") or "1").lower() in ("1","true","yes","on")
WARN_THROTTLE_SEC = int(cfg_str("XP_WARN_THROTTLE_SEC", "3600") or "3600")

class XpHistoryRenderOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_warn = 0.0
        self.client = UpstashClient() if UpstashClient else None

    async def _award(self, delta: int):
        if delta == 0: return
        if self.client and getattr(self.client, "enabled", False):
            try:
                await self.client.incrby(SENIOR_KEY, int(delta))
                log.info("[xp-render] +%s -> %s (upstash)", delta, SENIOR_KEY); return
            except Exception as e:
                self._warn_once(f"upstash incr fail: {e!r}")
        if not SILENT_NO_SHIM:
            self._warn_once("No XP award shim/client available; skipping award")

    def _warn_once(self, msg: str):
        now = time.time()
        if now - self._last_warn >= WARN_THROTTLE_SEC:
            self._last_warn = now
            log.warning("[xp-render] %s", msg)
        else:
            log.debug("[xp-render] %s (suppressed)", msg)

    async def award_from_render(self, delta: int | None = None):
        await self._award(int(delta if delta is not None else DELTA_DEFAULT))

async def setup(bot):
    await bot.add_cog(XpHistoryRenderOverlay(bot))
