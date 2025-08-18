# This cog is intentionally disabled to avoid duplicate presence/status messages.
# Sticky presence is handled by `presence_sticky.py` (forced to #log-botphising).

from discord.ext import commands
import logging
log = logging.getLogger(__name__)

class _DisabledPresence(commands.Cog):
    def __init__(self, bot): self.bot = bot
    @commands.Cog.listener()
    async def on_ready(self):
        log.info("[presence] duplicate announcer disabled: %s", __name__)

async def setup(bot):
    await bot.add_cog(_DisabledPresence(bot))