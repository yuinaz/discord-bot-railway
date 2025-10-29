from __future__ import annotations
import os, logging, asyncio
from typing import Optional
try:
    from discord.ext import commands
except Exception as _e:
    class _Dummy: ...
    commands = _Dummy()  # type: ignore
    def _noop(*a, **k): 
        def _wrap(f): 
            return f
        return _wrap
    commands.Cog = object  # type: ignore
    commands.Cog.listener = lambda *a, **k: _noop  # type: ignore

log = logging.getLogger(__name__)

def _extract_delta_and_user(*args, **kwargs):
    for k in ("amount","delta","xp","value"):
        if k in kwargs:
            try:
                return int(kwargs[k]), kwargs.get("user") or kwargs.get("member") or (args[0] if args else None)
            except Exception:
                pass
    if len(args) >= 2:
        try:
            amt = int(args[1]); return amt, args[0]
        except Exception:
            pass
    if len(args) >= 1:
        try:
            amt = int(args[0])
            if -100_000 <= amt <= 100_000: return amt, None
        except Exception:
            pass
    return 0, None

class XpEventBridgeOverlay(commands.Cog):  # type: ignore
    def __init__(self, bot):
        self.bot = bot
        self.url = os.getenv("UPSTASH_REDIS_REST_URL") or ""
        self.token = os.getenv("UPSTASH_REDIS_REST_TOKEN") or ""
        self.key = os.getenv("XP_SENIOR_KEY","xp:bot:senior_total")

    async def _incr(self, delta: int) -> Optional[int]:
        if not self.url or not self.token:
            log.debug("[xp-bridge] Upstash ENV missing; skip INCR")
            return None
        if delta <= 0 or abs(delta) > 100_000:
            log.info("[xp-bridge] skip INCR (delta=%s)", delta)
            return None
        try:
            import aiohttp
            async with aiohttp.ClientSession() as s:
                u = f"{self.url}/incrby/{self.key}/{delta}"
                async with s.get(u, headers={"Authorization": f"Bearer {self.token}"} ) as r:
                    if r.status != 200:
                        txt = await r.text()
                        raise RuntimeError(f"HTTP {r.status}: {txt}")
                    j = await r.json()
                    try: return int(j.get("result"))
                    except Exception: return None
        except Exception as e:
            log.warning("[xp-bridge] INCR err: %r (delta=%s) key=%s", e, delta, self.key)
            return None

    async def _handle(self, *a, **k):
        d, _ = _extract_delta_and_user(*a, **k)
        newv = await self._incr(d)
        if newv is not None:
            log.info("[xp-bridge] xp_add +%s () -> %s", d, self.key)

    @commands.Cog.listener()  # type: ignore
    async def on_xp_add(self, *a, **k):
        await self._handle(*a, **k)

    @commands.Cog.listener()  # type: ignore
    async def on_xp_award(self, *a, **k):
        await self._handle(*a, **k)

    @commands.Cog.listener()  # type: ignore
    async def on_satpam_xp(self, *a, **k):
        await self._handle(*a, **k)

async def setup(bot):  # discord.py 2.x
    try:
        rc = bot.remove_cog("XpEventBridgeOverlay")
        if asyncio.iscoroutine(rc):
            await rc
    except Exception:
        pass
    res = bot.add_cog(XpEventBridgeOverlay(bot))
    if asyncio.iscoroutine(res):
        await res

def setup_sync(bot):  # fallback for loaders expecting sync setup()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.run_until_complete(setup(bot))
