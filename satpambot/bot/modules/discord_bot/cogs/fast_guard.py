from __future__ import annotations
import logging
from discord.ext import commands

log = logging.getLogger(__name__)

class FastGuard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

async def setup(bot: commands.Bot):
    await bot.add_cog(FastGuard(bot))
