# a00_00_xp_kv_selfheal_overlay.py
from __future__ import annotations
import os, json, logging
from discord.ext import commands
try:
    import httpx
except Exception:
    httpx = None

log = logging.getLogger(__name__)
KEY = "xp:bot:senior_total"
URL = os.getenv("UPSTASH_REDIS_REST_URL", "").rstrip("/")
TOK = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")

class EarlyXpKvSelfHeal(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        try:
            bot.loop.create_task(self._heal())
        except Exception:
            pass

    async def _heal(self):
        if not (URL and TOK and httpx):
            return
        try:
            async with httpx.AsyncClient(timeout=10.0) as cli:
                r = await cli.get(f"{URL}/get/{KEY}", headers={"Authorization": f"Bearer {TOK}"})
                raw = (r.json() or {}).get("result")
                try:
                    int(raw); return
                except Exception:
                    pass
                val = None
                try:
                    obj = json.loads(raw) if isinstance(raw, str) else raw
                    if isinstance(obj, dict) and "senior_total_xp" in obj:
                        val = int(obj["senior_total_xp"])
                except Exception:
                    val = None
                if val is None:
                    return
                await cli.post(f"{URL}/set/{KEY}/{val}", headers={"Authorization": f"Bearer {TOK}"})
                log.info("[xp-selfheal] normalized %s -> %d", KEY, val)
        except Exception as e:
            log.debug("[xp-selfheal] early heal failed: %r", e)

async def setup(bot: commands.Bot):
    await bot.add_cog(EarlyXpKvSelfHeal(bot))
