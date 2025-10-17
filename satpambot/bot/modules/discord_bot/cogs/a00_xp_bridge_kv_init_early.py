# a00_xp_bridge_kv_init_early.py
import os, logging, httpx
from discord.ext import commands

log = logging.getLogger(__name__)

def _env(k, d=None):
    v = os.environ.get(k)
    return v if v not in (None, "") else d

class XpBridgeKvInitEarly(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.url = _env("UPSTASH_REDIS_REST_URL")
        self.tok = _env("UPSTASH_REDIS_REST_TOKEN")

    async def cog_load(self):
        # Run as early as possible to avoid bridge failing
        if not (self.url and self.tok):
            log.warning("[xp-kv-early] Upstash env missing; skip")
            return
        try:
            await self._ensure_key("xpbridge:last_total_xp", "0")
            log.info("[xp-kv-early] ensured xpbridge:last_total_xp exists")
        except Exception as e:
            log.warning("[xp-kv-early] ensure failed: %r", e)

    async def _ensure_key(self, key: str, default_val: str):
        headers = {"Authorization": f"Bearer {self.tok}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=10.0) as x:
            r = await x.post(self.url, headers=headers, json=["EXISTS", key])
            r.raise_for_status()
            ex = r.json().get("result", 0)
            if ex == 1:
                return
            r2 = await x.post(self.url, headers=headers, json=["SETNX", key, str(default_val)])
            r2.raise_for_status()

async def setup(bot):
    await bot.add_cog(XpBridgeKvInitEarly(bot))
