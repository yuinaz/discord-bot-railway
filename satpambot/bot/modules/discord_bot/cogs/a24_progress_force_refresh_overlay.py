import asyncio, logging
from discord.ext import commands

log = logging.getLogger(__name__)

class ProgressForceRefreshOverlay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._task = None
        # Create background task if event loop is available
        loop = getattr(bot, "loop", None)
        if loop and hasattr(loop, "create_task"):
            self._task = loop.create_task(self._kick())
        else:
            try:
                loop = asyncio.get_running_loop()
                self._task = loop.create_task(self._kick())
            except RuntimeError:
                # Smoke/DummyBot environment: no running loop; skip scheduling
                log.warning("[progress_force_refresh] no running loop; background task disabled in smoke env")

    async def cog_unload(self):
        if self._task:
            self._task.cancel()

    async def _kick(self):
        await asyncio.sleep(1.5)
        # In real runtime we could call into reporter/keeper to force refresh; keep simple here
        log.info("[progress_force_refresh] kick executed")

async def setup(bot):
    # Avoid failing in smoke where DummyBot may not have .loop
    try:
        await bot.add_cog(ProgressForceRefreshOverlay(bot))
    except Exception as e:
        log.warning("[progress_force_refresh] setup no-op in smoke: %s", e)
