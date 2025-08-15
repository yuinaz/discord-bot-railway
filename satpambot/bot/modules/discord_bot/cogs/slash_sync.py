
from __future__ import annotations
import asyncio, logging, os, random
from discord.ext import commands

log = logging.getLogger("slash_sync")

def _getfloat(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default

class SlashSync(commands.Cog):
    """Env-tunable slash sync with backoff to avoid 429/1015.
    Defaults: per-guild sync DISABLED unless SLASH_SYNC_PER_GUILD=1
    ENV:
      SLASH_SYNC_PER_GUILD=1|0
      SLASH_SYNC_SPACING=0.8
      SLASH_SYNC_BACKOFFS=2,4,8,15,30
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._task: asyncio.Task | None = None
        # default OFF for safety
        self._per_guild = os.getenv("SLASH_SYNC_PER_GUILD", "0") == "1"
        self._spacing = _getfloat("SLASH_SYNC_SPACING", 0.8)
        backoffs = os.getenv("SLASH_SYNC_BACKOFFS", "2,4,8,15,30")
        self._backoffs = [max(1.0, float(x)) for x in backoffs.split(",") if x.strip()]

    @commands.Cog.listener()
    async def on_ready(self):
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._sync_worker())

    async def _sync_worker(self):
        # 1) Global sync (murah). Backoff jika 429.
        for i, base in enumerate(self._backoffs, start=1):
            try:
                await self.bot.tree.sync()
                log.info("[slash] global sync ok")
                break
            except Exception as e:
                msg = str(e)
                if "429" in msg or "rate limit" in msg.lower():
                    wait = float(base) + random.uniform(0, 0.5*float(base))
                    log.warning("[slash] global sync rate-limited (try %d), sleeping %.1fs", i, wait)
                    await asyncio.sleep(wait)
                    continue
                log.warning("[slash] global sync failed: %s", e)
                break

        # 2) Opsional: per-guild sync, default OFF
        if not self._per_guild:
            log.info("[slash] per-guild sync disabled by default (set SLASH_SYNC_PER_GUILD=1 to enable)")
            return

        guilds = list(self.bot.guilds)
        for idx, g in enumerate(guilds, start=1):
            try:
                await self.bot.tree.sync(guild=g)
                log.info("[slash] synced guild: %s (%d/%d)", g.name, idx, len(guilds))
            except Exception as e:
                msg = str(e)
                if "429" in msg or "rate limit" in msg.lower():
                    log.warning("[slash] guild sync 429 on %s; skipping for now", g.name)
                else:
                    log.warning("[slash] guild sync failed on %s: %s", g.name, e)
            await asyncio.sleep(self._spacing)

async def setup(bot: commands.Bot):
    await bot.add_cog(SlashSync(bot))
