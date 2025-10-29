from __future__ import annotations
from discord.ext import commands
class _Noop(commands.Cog):
    """noop"""
    def __init__(self, bot): self.bot = bot
async def setup(bot: commands.Bot):
    await bot.add_cog(_Noop(bot))
