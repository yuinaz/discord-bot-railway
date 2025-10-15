import logging
from collections import defaultdict
from discord.ext import commands

log = logging.getLogger(__name__)

class CogHealth(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.errors = defaultdict(int)
        self.threshold = 5

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        name = ctx.cog.__class__.__name__ if ctx.cog else "NoCog"
        self.errors[name] += 1
        if self.errors[name] >= self.threshold:
            log.warning("[cog-health] %s over threshold.", name)

async def setup(bot):
    await bot.add_cog(CogHealth(bot))