import asyncio, logging
from discord.ext import commands

log = logging.getLogger(__name__)

class XpBridgeSoftRetry(commands.Cog):
    """Soft retry if Upstash KV not yet ready to avoid noisy WARN on cold boot."""
    def __init__(self, bot):
        self.bot = bot
        self._task = bot.loop.create_task(self._poke())

    async def _poke(self):
        await asyncio.sleep(5)
        try:
            # If target cog exposes a 'kick' or 'refresh' method, call it; else noop.
            target = self.bot.get_cog("XpBridgeFromStore") or self.bot.get_cog("XpBridgeFromStoreOverlay")
            if target and hasattr(target, "refresh"):
                await target.refresh()  # type: ignore
                log.info("[xpbridge-soft] refresh triggered")
        except Exception as e:
            log.info("[xpbridge-soft] skip/noop: %s", e)

async def setup(bot):
    await bot.add_cog(XpBridgeSoftRetry(bot))
