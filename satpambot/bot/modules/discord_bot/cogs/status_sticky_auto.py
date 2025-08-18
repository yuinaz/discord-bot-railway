from __future__ import annotations
from discord.ext import commands, tasks
try:
    from satpambot.bot.modules.discord_bot.helpers import log_utils
except Exception:
    import importlib; log_utils = importlib.import_module("satpambot.bot.modules.discord_bot.helpers.log_utils")
class StatusStickyAuto(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        try: self._heartbeat.start()
        except Exception: pass
    @commands.Cog.listener()
    async def on_ready(self):
        for g in getattr(self.bot, "guilds", []):
            await log_utils.upsert_status_embed(self.bot, g)
    @tasks.loop(minutes=5)
    async def _heartbeat(self):
        for g in getattr(self.bot, "guilds", []):
            await log_utils.upsert_status_embed(self.bot, g)
    @_heartbeat.before_loop
    async def _before(self):
        if hasattr(self.bot, "wait_until_ready"):
            await self.bot.wait_until_ready()
async def setup(bot): await bot.add_cog(StatusStickyAuto(bot))
