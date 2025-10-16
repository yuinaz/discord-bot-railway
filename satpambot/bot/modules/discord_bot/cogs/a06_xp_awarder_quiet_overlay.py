
"""
Reduce noisy logs from XP awarder overlay without changing behavior.
"""
import logging
from discord.ext import commands

QUIET_LOGGERS = [
    "satpambot.bot.modules.discord_bot.cogs.a08_xp_message_awarder_overlay",
    "modules.discord_bot.cogs.a08_xp_message_awarder_overlay",
]

class XPAwarderQuietOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        for name in QUIET_LOGGERS:
            logging.getLogger(name).setLevel(logging.INFO)

async def setup(bot):
    await bot.add_cog(XPAwarderQuietOverlay(bot))
