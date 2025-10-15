
"""
Quiet noisy httpx/httpcore/urllib3 INFO logs (e.g., 403/401 lines) without touching main config.
"""
import logging
from discord.ext import commands

class HTTPXLogQuietener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        for name in ("httpx", "httpcore", "urllib3.connectionpool"):
            logging.getLogger(name).setLevel(logging.WARNING)

async def setup(bot):
    await bot.add_cog(HTTPXLogQuietener(bot))