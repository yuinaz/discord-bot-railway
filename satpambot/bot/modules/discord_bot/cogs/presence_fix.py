from __future__ import annotations
from discord.ext import commands
try:
    from satpambot.bot.modules.discord_bot.helpers import log_utils
except Exception:
    import importlib; log_utils = importlib.import_module("satpambot.bot.modules.discord_bot.helpers.log_utils")
class PresenceFix(commands.Cog):
    def __init__(self, bot): self.bot = bot
    @commands.Cog.listener()
    async def on_presence_update(self, before, after):
        if getattr(after, "guild", None) is not None:
            await log_utils.upsert_status_embed(self.bot, after.guild)
async def setup(bot): await bot.add_cog(PresenceFix(bot))
