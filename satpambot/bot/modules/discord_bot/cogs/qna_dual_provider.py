from __future__ import annotations

from discord.ext import commands

import logging

LOGGER = logging.getLogger(__name__)
QNA_CHANNEL_ID = 1426571542627614772

class QnaDualProvider(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        LOGGER.info("QnA ready (static id=%s)", QNA_CHANNEL_ID)
async def setup(bot: commands.Bot):
    await bot.add_cog(QnaDualProvider(bot))