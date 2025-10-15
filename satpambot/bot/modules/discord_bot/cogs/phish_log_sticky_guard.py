from __future__ import annotations

import logging
from discord.ext import commands

LOGGER = logging.getLogger(__name__)

class PhishLogStickyGuard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

async def setup(bot: commands.Bot):
    await bot.add_cog(PhishLogStickyGuard(bot))
