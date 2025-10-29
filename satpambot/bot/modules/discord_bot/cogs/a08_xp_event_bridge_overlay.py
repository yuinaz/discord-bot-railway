from __future__ import annotations
import os, logging, asyncio
from typing import Optional
from discord.ext import commands

log = logging.getLogger(__name__)

def _int(v, d=0):
    try:
        return int(v)
    except Exception:
        try:
            return int(float(v))
        except Exception:
            return d

class XpEventBridgeOverlay(commands.Cog):
    """
    Bridge XP events to Upstash INCRBY with guards:
    - Skip if delta <= 0 (avoid 400 Bad Request)
    - Soft-fail if Upstash env missing
    - Do NOT write pinned JSON here (handled by dual mirror overlay)
    """
    def __init__(self, bot):
        self.bot = bot
        self.url = os.getenv("UPSTASH_REDIS_REST_URL") or ""
        self.token = os.getenv("UPSTASH_REDIS_REST_TOKEN") or ""
        self.key = os.getenv("XP_SENIOR_KEY","xp:bot:senior_total")

    async def _incr(self, delta: int) -> Optional[int]:
        if not self.url or not self.token:
            log.debug("[xp-bridge] Upstash ENV missing; skip INCR")
            return None
        if delta <= 0:
            log.info("[xp-bridge] skip INCR (delta=%s)", delta)
            return None
        try:
            import aiohttp
            async with aiohttp.ClientSession() as s:
                incr_url = f"{self.url}/incrby/{self.key}/{delta}"
                async with s.get(incr_url, headers={"Authorization": f"Bearer {self.token}"} ) as r:
                    if r.status != 200:
                        txt = await r.text()
                        raise RuntimeError(f"HTTP {r.status}: {txt}")
                    j = await r.json()
                    # Upstash returns {"result":"<new_value>"} typically
                    try:
                        return int(j.get("result"))
                    except Exception:
                        return None
        except Exception as e:
            log.warning("[xp-bridge] INCR err: %r (delta=%s) key=%s", e, delta, self.key)
            return None

    def _extract_delta(self, *args, **kwargs) -> int:
        for k in ("amount","delta","xp","value"):
            if k in kwargs:
                return _int(kwargs.get(k), 0)
        # Fallback: sometimes first arg is amount
        if args:
            return _int(args[0], 0)
        return 0

    async def _handle(self, *args, **kwargs):
        d = self._extract_delta(*args, **kwargs)
        newv = await self._incr(d)
        if newv is not None:
            log.info("[xp-bridge] xp_add +%s () -> %s", d, self.key)

    @commands.Cog.listener()
    async def on_xp_add(self, *args, **kwargs):
        await self._handle(*args, **kwargs)

    @commands.Cog.listener()
    async def on_xp_award(self, *args, **kwargs):
        await self._handle(*args, **kwargs)

    @commands.Cog.listener("on_satpam_xp")
    async def on_satpam_xp(self, *args, **kwargs):
        await self._handle(*args, **kwargs)

async def setup(bot: commands.Bot):
    # ensure older version removed to prevent duplicate handling
    try:
        bot.remove_cog("XpEventBridgeOverlay")
    except Exception:
        pass
    await bot.add_cog(XpEventBridgeOverlay(bot))
