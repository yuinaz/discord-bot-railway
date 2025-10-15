from __future__ import annotations

import asyncio
import logging
import os
from discord.ext import commands

LOGGER = logging.getLogger(__name__)

class LearningPassiveObserverPersist(commands.Cog):
    """No-op safety cog (kept for compatibility)."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Nothing heavy here — main persist happens inline in observer.

async def setup(bot: commands.Bot):
    await bot.add_cog(LearningPassiveObserverPersist(bot))
