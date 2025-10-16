
# a00_strict_warning_filter_overlay.py (v6.1)
import os, warnings, logging
from discord.ext import commands
logger = logging.getLogger(__name__)

class StrictWarnFilter(commands.Cog):
    def __init__(self, bot): self.bot = bot
    @commands.Cog.listener()
    async def on_ready(self):
        if os.getenv("STRICT_NO_WARN","0") != "1":
            return
        for cat in (DeprecationWarning, RuntimeWarning, ResourceWarning):
            warnings.filterwarnings("ignore", category=cat)
        # Set discord.client logger level to ERROR
        logging.getLogger("discord.client").setLevel(logging.ERROR)
        logger.info("[warn-filter] STRICT_NO_WARN=1 active")
async def setup(bot):
    await bot.add_cog(StrictWarnFilter(bot))
