
from __future__ import annotations
import logging, asyncio
from discord.ext import commands

log = logging.getLogger(__name__)

try:
    from ..helpers.xp_total_resolver import stage_preferred, resolve_senior_total
except Exception as e:
    log.warning("[autorank] helper import failed: %s; using fallbacks", e)
    async def stage_preferred(): return ("KULIAH-S1", 0.0, {"start_total":0,"required":19000,"current":0})
    async def resolve_senior_total(): return 0

class LadderRuntimeAutorankOverlay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._task = None

    async def start(self):
        if self._task is None:
            self._task = asyncio.create_task(self._periodic())

    async def _periodic(self):
        await asyncio.sleep(5.0)
        while not self.bot.is_closed():
            try:
                label, pct, _meta = await stage_preferred()
                total = await resolve_senior_total()
                log.warning("[autorank] %s (%.1f%%) xp=%s", label, pct, total)
            except Exception as e:
                log.warning("[autorank] soft-fail: %s", e)
            await asyncio.sleep(180)

async def setup(bot: commands.Bot):
    cog = LadderRuntimeAutorankOverlay(bot)
    await bot.add_cog(cog)
    await cog.start()
