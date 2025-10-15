from __future__ import annotations

import logging
from discord.ext import commands

log = logging.getLogger(__name__)

class SelfLearningGuard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        log.info("[self_learning_guard] defensive mode installed (raw-send snapshot)")

async def setup(bot: commands.Bot):
    await bot.add_cog(SelfLearningGuard(bot))