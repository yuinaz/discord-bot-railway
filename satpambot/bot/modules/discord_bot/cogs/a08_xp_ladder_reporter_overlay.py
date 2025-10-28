
from __future__ import annotations
import logging, asyncio
from discord.ext import commands

log = logging.getLogger(__name__)

try:
    from ..helpers.xp_total_resolver import resolve_senior_total, stage_from_total
except Exception as e:
    log.warning("[xp-ladder] helper import failed: %s; using fallbacks", e)
    async def resolve_senior_total(): return None
    def stage_from_total(total: int): return "KULIAH-S1", 0.0, {"start_total": 0, "required": 19000}

class XpLadderReporterOverlay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._task = None

    async def start(self):
        if self._task is None:
            self._task = asyncio.create_task(self._periodic())

    async def _periodic(self):
        await asyncio.sleep(3.0)
        while not self.bot.is_closed():
            try:
                total = await resolve_senior_total()
                if total is None:
                    await asyncio.sleep(30)
                    continue
                label, pct, meta = stage_from_total(int(total))
                # HANYA laporan KULIAH
                log.info("[xp-ladder] total=%s -> %s (band %s..%s, %.1f%%)", total, label, meta.get("start_total"), meta.get("required"), pct)
            except Exception as e:
                log.warning("[xp-ladder] reporter soft-fail: %s", e)
            await asyncio.sleep(120)

async def setup(bot: commands.Bot):
    cog = XpLadderReporterOverlay(bot)
    await bot.add_cog(cog)
    await cog.start()
