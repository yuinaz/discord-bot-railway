from __future__ import annotations

import logging
from discord.ext import commands

LOGGER = logging.getLogger(__name__)

class StatusCoalescerWildcard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        LOGGER.info("StatusCoalescerWildcard active.")

async def setup(bot: commands.Bot):
    await bot.add_cog(StatusCoalescerWildcard(bot))
