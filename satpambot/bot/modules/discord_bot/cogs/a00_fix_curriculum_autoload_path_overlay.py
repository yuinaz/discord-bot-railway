
import asyncio, logging
from pathlib import Path
from discord.ext import commands

log = logging.getLogger(__name__)

class FixCurriculumAutoloadPath(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._task = asyncio.create_task(self._patch())

    async def _patch(self):
        await self.bot.wait_until_ready()
        count = 0
        for name, cog in list(self.bot.cogs.items()):
            try:
                p = getattr(cog, "status_json_path", None)
                if isinstance(p, str):
                    newp = Path(p)
                    try:
                        newp.parent.mkdir(parents=True, exist_ok=True)
                    except Exception:
                        pass
                    setattr(cog, "status_json_path", newp)
                    count += 1
                    log.warning("[curriculum_autoload_fix] coerced %s.status_json_path -> Path(%r)", name, str(newp))
            except Exception as e:
                log.exception("[curriculum_autoload_fix] failed on %s: %r", name, e)
        if not count:
            log.info("[curriculum_autoload_fix] nothing to patch")

    async def cog_unload(self):
        try: self._task.cancel()
        except Exception: pass

def _inject(bot):
    flag = "_fix_curriculum_autoload_path_overlay_loaded"
    if getattr(bot, flag, False): return
    setattr(bot, flag, True)
    bot.add_cog(FixCurriculumAutoloadPath(bot))

def setup(bot): _inject(bot)
async def setup(bot): _inject(bot)
