from __future__ import annotations
import logging, re
from discord.ext import commands
import discord

log = logging.getLogger(__name__)

class AntiImagePhishAdvanced(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Placeholder: no-op to keep compilation stable
        return

async def setup(bot: commands.Bot):
    await bot.add_cog(AntiImagePhishAdvanced(bot))
