import os, json, asyncio, logging
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks

from ..helpers.compat_learning_status import read_learning_status

log = logging.getLogger(__name__)

class LearningStatusAutopin(commands.Cog):
    """Safe autopin/refresher for learning status."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.period = max(60, int(os.getenv("LEARNING_AUTOPIN_PERIOD_SEC","300") or "300"))
        self.channel_id = None
        try:
            self.channel_id = int(os.getenv("LEARNING_STATUS_CHANNEL_ID","") or "0") or None
        except Exception:
            self.channel_id = None
        if self.channel_id:
            self.task = self.loop.start()
        else:
            log.info("[autopin] no channel set; passive mode")

    def cog_unload(self):
        try: self.loop.cancel()
        except Exception: pass

    @tasks.loop(seconds=30)
    async def loop(self):
        try:
            now = datetime.now(timezone.utc)
            if int(now.timestamp()) % self.period != 0:
                return
            ch = None
            if self.channel_id:
                ch = self.bot.get_channel(self.channel_id) or await self.bot.fetch_channel(self.channel_id)
            if not ch:
                return
            base = os.getenv("UPSTASH_REDIS_REST_URL","").rstrip("/")
            token = os.getenv("UPSTASH_REDIS_REST_TOKEN","")
            if not (base and token):
                return
            import aiohttp
            async with aiohttp.ClientSession() as session:
                s = await read_learning_status(session, base, token)
            txt = f"📚 {s['label']} • {s['percent']:.1f}% (rem {s['remaining']})"
            await ch.send(txt)
        except Exception as e:
            log.warning("[learn-status] refresh failed: %r", e)

    @loop.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(LearningStatusAutopin(bot))
