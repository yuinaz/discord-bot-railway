
# a00_import_compat_alias_overlay.py (v7.4)
import sys, importlib, logging
from discord.ext import commands
log = logging.getLogger(__name__)
def _alias(path: str, target: str) -> bool:
    try:
        mod = importlib.import_module(target)
        sys.modules[path] = mod
        return True
    except Exception as e:
        log.info("[import-alias] cannot alias %s -> %s: %r", path, target, e)
        return False
class ImportCompatAlias(commands.Cog):
    def __init__(self, bot): self.bot = bot
    @commands.Cog.listener()
    async def on_ready(self):
        ok1 = _alias("modules", "satpambot.bot.modules")
        ok2 = _alias("modules.discord_bot", "satpambot.bot.modules.discord_bot")
        ok3 = _alias("modules.discord_bot.cogs", "satpambot.bot.modules.discord_bot.cogs")
        log.info("[import-alias] compat active: modules=%s discord_bot=%s cogs=%s", ok1, ok2, ok3)
async def setup(bot):
    try: await bot.add_cog(ImportCompatAlias(bot))
    except Exception as e: log.info("[import-alias] setup swallowed: %r", e)
