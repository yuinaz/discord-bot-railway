from __future__ import annotations
import logging
from discord.ext import commands
from satpambot.config.local_cfg import cfg

log = logging.getLogger(__name__)

class PersonaOverlay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        log.info("[persona_overlay] using local cfg; mentions_only=%s", cfg("CHAT_MENTIONS_ONLY", True))

async def setup(bot: commands.Bot):
    await bot.add_cog(PersonaOverlay(bot))