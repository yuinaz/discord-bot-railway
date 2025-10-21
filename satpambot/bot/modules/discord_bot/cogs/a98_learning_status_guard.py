import os, json, asyncio, logging
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks

from ..helpers.rank_utils import is_lower

log = logging.getLogger(__name__)

class _Upstash:
    def __init__(self):
        self.url = os.getenv("UPSTASH_REDIS_REST_URL", "").rstrip("/")
        self.token = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
        self.enabled = bool(self.url and self.token and os.getenv("KV_BACKEND","").lower()=="upstash_rest")

    async def _get_json(self, session, path: str):
        import aiohttp
        headers = {"Authorization": f"Bearer {self.token}"}
        async with session.get(f"{self.url}{path}", headers=headers, timeout=15) as r:
            r.raise_for_status()
            return await r.json()

    async def get(self, session, key: str):
        if not self.enabled: return None
        try:
            j = await self._get_json(session, f"/get/{key}")
            return j.get("result")
        except Exception:
            return None

    async def pipeline(self, session, commands):
        if not self.enabled or not commands: return False
        import aiohttp
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        async with session.post(f"{self.url}/pipeline", headers=headers, json=commands, timeout=15) as r:
            try:
                r.raise_for_status()
                return True
            except Exception:
                return False

upstash = _Upstash()

class LearningStatusGuard(commands.Cog):
    """Watchdog: restore peak label if someone writes a lower label."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.period = max(30, int(os.getenv("LEARNING_GUARD_PERIOD_SEC","60") or "60"))
        self.task = self.loop.start()

    def cog_unload(self):
        try: self.loop.cancel()
        except Exception: pass

    @tasks.loop(seconds=30)
    async def loop(self):
        if not upstash.enabled: return
        now = datetime.now(timezone.utc)
        if int(now.timestamp()) % self.period != 0: return
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                raw = await upstash.get(session, "learning:status_json")
                if not raw: return
                try:
                    j = json.loads(raw)
                    live = j.get("label")
                except Exception:
                    return
                # check max
                max_label = await upstash.get(session, "learning:last_max_label")
                if max_label and isinstance(max_label, str):
                    max_label = max_label.strip('"')
                # update max if live > max
                from ..helpers.rank_utils import is_lower
                if not max_label or is_lower(max_label, live):
                    await upstash.pipeline(session, [["SET","learning:last_max_label", live]])
                    return
                # restore if live < max
                if is_lower(live, max_label):
                    phase = (max_label.split("-")[0]) if max_label else "SMP"
                    status = f"{max_label} (100.0%)"
                    status_json = json.dumps({"label":max_label}, separators=(",",":"))
                    await upstash.pipeline(session, [
                        ["SET","learning:status", status],
                        ["SET","learning:status_json", status_json],
                        ["SET","learning:phase", phase],
                    ])
        except Exception as e:
            pass

    @loop.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(LearningStatusGuard(bot))
