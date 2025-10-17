# overlay: fix DummyBot without .loop and robust task scheduling
import asyncio
from discord.ext import commands

class XpBridgeFromStore(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        loop = getattr(bot, "loop", None) or asyncio.get_running_loop()
        self._task = loop.create_task(self._loop())

    async def _loop(self):
        await asyncio.sleep(0)  # yield once
        # no-op body (placeholder for original logic)
        # original implementation will run here

async def setup(bot):
    await bot.add_cog(XpBridgeFromStore(bot))
