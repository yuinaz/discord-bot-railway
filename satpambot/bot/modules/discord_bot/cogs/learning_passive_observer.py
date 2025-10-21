import os, asyncio, logging, json
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks

log = logging.getLogger(__name__)

class _Upstash:
    def __init__(self):
        self.url = os.getenv("UPSTASH_REDIS_REST_URL", "").rstrip("/")
        self.token = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
        self.enabled = bool(self.url and self.token and os.getenv("KV_BACKEND","").lower()=="upstash_rest")

    async def incrby(self, session, key: str, delta: int):
        if not self.enabled: return None
        import aiohttp
        headers = {"Authorization": f"Bearer {self.token}"}
        async with session.post(f"{self.url}/incrby/{key}/{int(delta)}", headers=headers, timeout=15) as r:
            r.raise_for_status()
            try:
                j = await r.json()
                return int(j.get("result")) if "result" in j else None
            except Exception:
                return None

upstash = _Upstash()

def _parse_id_csv(s: str):
    out = set()
    for part in (s or "").split(","):
        part = part.strip()
        if not part: continue
        try: out.add(int(part))
        except Exception: pass
    return out

class LearningPassiveObserver(commands.Cog):
    """Leina: batched passive XP → xp:bot:senior_total (daily cap)."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._per_msg = max(0, int(os.getenv("LEARNING_PASSIVE_XP_PER_MESSAGE", "1") or "1"))
        self._daily_cap = max(0, int(os.getenv("LEARNING_PASSIVE_DAILY_CAP", "300") or "300"))
        self._allow_guilds = _parse_id_csv(os.getenv("LEARNING_PASSIVE_ALLOW_GUILDS",""))
        self._deny_channels = _parse_id_csv(os.getenv("LEARNING_PASSIVE_DENY_CHANNELS",""))
        self._bucket = 0
        self._today = None
        self._task = self._flush.start()

    def cog_unload(self):
        try:
            self._flush.cancel()
        except Exception:
            pass

    def _same_day(self, dt: datetime) -> bool:
        if self._today is None: return False
        return dt.date() == self._today

    @tasks.loop(seconds=10)
    async def _flush(self):
        if not upstash.enabled: return
        if self._bucket <= 0: return
        now = datetime.now(timezone.utc)
        if not self._same_day(now):
            self._today = now.date()
            self._bucket = min(self._bucket, self._daily_cap)
        delta = min(self._bucket, self._daily_cap)
        if delta <= 0: 
            return
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                await upstash.incrby(session, "xp:bot:senior_total", int(delta))
        except Exception as e:
            log.debug("[passive] flush failed: %s", e)
            return
        finally:
            self._bucket = 0

    @_flush.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()
        self._today = datetime.now(timezone.utc).date()

    @commands.Cog.listener("on_message")
    async def _on_message(self, message: discord.Message):
        if message.author.bot: 
            return
        if self._per_msg <= 0:
            return
        if self._deny_channels and message.channel.id in self._deny_channels:
            return
        if self._allow_guilds and message.guild and (message.guild.id not in self._allow_guilds):
            return
        self._bucket = min(self._bucket + self._per_msg, self._daily_cap)

async def setup(bot: commands.Bot):
    await bot.add_cog(LearningPassiveObserver(bot))
